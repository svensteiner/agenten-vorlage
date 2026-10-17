from __future__ import annotations

import hashlib
import json
import multiprocessing
import subprocess
import sys
import tempfile
import unittest
from multiprocessing.connection import Connection
from pathlib import Path
from unittest.mock import patch

from agentkit.contracts import ContractError
from agentkit.phase_test_execution import (
    LocalPhaseTestPolicy,
    authorize_phase,
    verify_phase_freshness,
)
from agentkit.phase_test_runner import (
    _IMAGE_ENV,
    _PYTEST_CHILD,
    _RESULT_MARKER,
    _classify_container_result,
    _docker_create_args,
    _host_runner_sha256,
    _phase_result_from_output,
    _snapshot,
    _stage_git_required,
    _valid_container,
    _valid_image,
    _valid_result,
    run_phase,
    validate_phase_receipt,
)


def _spawn_send(connection: Connection, value: str) -> None:
    connection.send(value)
    connection.close()


class LocalPhaseTestRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.workspace = root / "workspace"
        self.workspace.mkdir()
        self.host = root / "host"
        self.host.mkdir()
        source = self.workspace / "agentkit" / "worker.py"
        source.parent.mkdir()
        source.write_text("def work(): return 1\n", encoding="utf-8")
        test = self.workspace / "tests" / "test_worker.py"
        test.parent.mkdir()
        test.write_text("def test_change(): assert False\n", encoding="utf-8")
        self.manifest = self.host / "phase.json"
        self.data = {
            "version": 1,
            "image_ref": "registry.example/agentkit@sha256:" + "a" * 64,
            "image_id": "sha256:" + "a" * 64,
            "dependency_lock_sha256": "b" * 64,
            "host_runner_sha256": _host_runner_sha256(),
            "production_files": [
                {
                    "path": "agentkit/worker.py",
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                }
            ],
            "snapshot_paths": ["agentkit/worker.py", "tests/test_worker.py"],
            "allowed_write_paths": ["agentkit/worker.py", "tests/test_worker.py"],
            "phases": {
                "red": {
                    "nodeids": ["tests/test_worker.py::test_change"],
                    "expected_failure_nodeids": ["tests/test_worker.py::test_change"],
                },
                "targeted": {"nodeids": ["tests/test_worker.py::test_change"]},
                "full": {"test_files": ["tests/test_worker.py"]},
            },
            "full_test_roots": ["tests"],
            "full_minimum_test_count": 1,
            "limits": {
                "timeout_seconds": 60,
                "memory_bytes": 64 * 1024**2,
                "memory_swap_bytes": 64 * 1024**2,
                "nano_cpus": 1_000_000_000,
                "pids": 32,
                "output_bytes": 200_000,
                "nofile": 64,
                "tmpfs_bytes": 16 * 1024**2,
                "max_file_bytes": 2 * 1024**2,
                "max_snapshot_bytes": 8 * 1024**2,
            },
        }
        self.manifest.write_text(json.dumps(self.data), encoding="utf-8")
        self.policy = LocalPhaseTestPolicy.from_file(self.manifest, self.workspace)

    def tearDown(self):
        self.temp.cleanup()

    def test_snapshot_contains_only_operator_paths_and_matches_freshness(self):
        freshness = verify_phase_freshness(self.policy, self.workspace, "red")
        stage = Path(self.temp.name) / "stage"
        stage.mkdir()
        archive, digest = _snapshot(
            self.policy,
            self.workspace,
            freshness,
            authorize_phase(self.policy, "red"),
            stage,
        )
        self.assertTrue(archive.is_file())
        self.assertEqual(64, len(digest))
        import tarfile

        with tarfile.open(archive, "r:") as tar:
            self.assertEqual(
                set(self.policy.snapshot_paths)
                | {
                    "__agentkit_phase_control_v1__.json",
                    "__agentkit_phase_child_v1__.py",
                },
                set(tar.getnames()),
            )
            self.assertFalse(any(name.startswith(".git/") for name in tar.getnames()))
            control = json.load(tar.extractfile("__agentkit_phase_control_v1__.json"))
            self.assertFalse(control["initialize_git"])

    def test_stage_git_fixture_requires_declared_root_gitignore(self):
        self.assertFalse(_stage_git_required(self.policy))
        gitignore = self.workspace / ".gitignore"
        gitignore.write_text("*.cache\n", encoding="utf-8")
        self.data["snapshot_paths"] = [
            ".gitignore",
            *self.data["snapshot_paths"],
        ]
        self.manifest.write_text(json.dumps(self.data), encoding="utf-8")
        self.policy = LocalPhaseTestPolicy.from_file(self.manifest, self.workspace)
        self.assertTrue(_stage_git_required(self.policy))

    def test_red_accepts_assertion_failure_but_rejects_value_error(self):
        plan = authorize_phase(self.policy, "red")
        ids = list(plan.nodeids)
        files = ["tests/test_worker.py"]
        base = {
            "schema": "agentkit/local-phase-result-v1",
            "phase": "red",
            "exit_code": 1,
            "nodeids": ids,
            "nodeids_sha256": hashlib.sha256(
                json.dumps(ids, separators=(",", ":")).encode()
            ).hexdigest(),
            "files": files,
            "files_sha256": hashlib.sha256(
                json.dumps(files, separators=(",", ":")).encode()
            ).hexdigest(),
            "post_hashes": verify_phase_freshness(self.policy, self.workspace, "red")[
                "input_hashes"
            ],
        }
        base["outcomes"] = {
            ids[0]: {
                "outcome": "failed",
                "exception_type": "AssertionError",
                "when": "call",
            }
        }
        ok, reason, _ = _valid_result(
            base,
            plan,
            self.policy,
            verify_phase_freshness(self.policy, self.workspace, "red"),
            1,
        )
        self.assertTrue(ok)
        self.assertEqual("expected_red_reproduced", reason)
        base["outcomes"][ids[0]] = {
            "outcome": "failed",
            "exception_type": "ValueError",
            "when": "call",
        }
        ok, reason, _ = _valid_result(
            base,
            plan,
            self.policy,
            verify_phase_freshness(self.policy, self.workspace, "red"),
            1,
        )
        self.assertFalse(ok)
        self.assertEqual("red_assertion_not_reproduced", reason)

    def test_red_rejects_internal_or_signal_exit_codes(self):
        plan = authorize_phase(self.policy, "red")
        nodeid = plan.nodeids[0]
        files = ["tests/test_worker.py"]
        result = {
            "schema": "agentkit/local-phase-result-v1",
            "phase": "red",
            "exit_code": 1,
            "nodeids": [nodeid],
            "nodeids_sha256": hashlib.sha256(
                json.dumps([nodeid], separators=(",", ":")).encode()
            ).hexdigest(),
            "files": files,
            "files_sha256": hashlib.sha256(
                json.dumps(files, separators=(",", ":")).encode()
            ).hexdigest(),
            "outcomes": {
                nodeid: {
                    "outcome": "failed",
                    "exception_type": "AssertionError",
                    "when": "call",
                }
            },
            "post_hashes": verify_phase_freshness(self.policy, self.workspace, "red")[
                "input_hashes"
            ],
        }
        for code in (2, 124, 137, 143):
            with self.subTest(container_exit_code=code):
                ok, reason, _ = _valid_result(
                    result,
                    plan,
                    self.policy,
                    verify_phase_freshness(self.policy, self.workspace, "red"),
                    code,
                )
                self.assertFalse(ok)
                self.assertEqual("exit_code_invalid", reason)

    def test_targeted_result_must_match_actual_container_exit(self):
        plan = authorize_phase(self.policy, "targeted")
        nodeids = list(plan.nodeids)
        files = ["tests/test_worker.py"]
        result = {
            "schema": "agentkit/local-phase-result-v1",
            "phase": "targeted",
            "exit_code": 0,
            "nodeids": nodeids,
            "nodeids_sha256": hashlib.sha256(
                json.dumps(nodeids, separators=(",", ":")).encode()
            ).hexdigest(),
            "files": files,
            "files_sha256": hashlib.sha256(
                json.dumps(files, separators=(",", ":")).encode()
            ).hexdigest(),
            "outcomes": {
                nodeids[0]: {
                    "outcome": "passed",
                    "exception_type": None,
                    "when": "call",
                }
            },
            "post_hashes": verify_phase_freshness(
                self.policy, self.workspace, "targeted"
            )["input_hashes"],
        }
        ok, reason, _ = _valid_result(
            result,
            plan,
            self.policy,
            verify_phase_freshness(self.policy, self.workspace, "targeted"),
            1,
        )
        self.assertFalse(ok)
        self.assertEqual("exit_code_invalid", reason)

    def test_container_exit_status_and_supervisor_report_are_consistent(self):
        plan = authorize_phase(self.policy, "targeted")
        nodeids = list(plan.nodeids)
        files = ["tests/test_worker.py"]
        freshness = verify_phase_freshness(self.policy, self.workspace, "targeted")
        report = {
            "schema": "agentkit/local-phase-result-v1",
            "phase": "targeted",
            "exit_code": 0,
            "nodeids": nodeids,
            "nodeids_sha256": hashlib.sha256(
                json.dumps(nodeids, separators=(",", ":"), ensure_ascii=False).encode()
            ).hexdigest(),
            "files": files,
            "files_sha256": hashlib.sha256(
                json.dumps(files, separators=(",", ":"), ensure_ascii=False).encode()
            ).hexdigest(),
            "outcomes": {
                nodeids[0]: {
                    "outcome": "passed",
                    "exception_type": None,
                    "when": "call",
                }
            },
            "post_hashes": freshness["input_hashes"],
        }
        status, reason, code, _ = _classify_container_result(
            0, report, plan, self.policy, freshness
        )
        self.assertEqual(("passed", "ok", 0), (status, reason, code))
        for timeout_code in (124, 137, 143):
            with self.subTest(timeout_code=timeout_code):
                status, reason, code, _ = _classify_container_result(
                    timeout_code, report, plan, self.policy, freshness
                )
                self.assertEqual("unknown", status)
                self.assertEqual("container_timeout_or_signal_exit", reason)
                self.assertIsNone(code)
        status, reason, code, _ = _classify_container_result(
            1, report, plan, self.policy, freshness
        )
        self.assertEqual("unknown", status)
        self.assertEqual("container_exit_result_mismatch", reason)
        self.assertIsNone(code)

    def test_docker_args_are_policy_selected_and_confined(self):
        plan = authorize_phase(self.policy, "targeted")
        args = _docker_create_args(
            self.policy, "/stage/source.tar", "agentkit-phase-targeted-abc", plan, 30
        )
        self.assertIn("--network=none", args)
        self.assertIn("--read-only", args)
        self.assertIn("--cap-drop=ALL", args)
        self.assertIn("--security-opt=no-new-privileges", args)
        self.assertIn(
            "type=bind,source=/stage/source.tar,target=/source.tar,readonly", args
        )
        self.assertEqual(
            self.policy.image_ref, args[args.index("--entrypoint=/usr/bin/timeout") + 1]
        )
        self.assertNotIn("tests/test_other.py::test_injected", args)

    def test_image_environment_must_match_audited_exact_profile(self):
        image = {
            "Id": self.policy.image_id,
            "Config": {
                "Env": [f"{key}={value}" for key, value in _IMAGE_ENV.items()],
                "Labels": {
                    "org.agentkit.test-lock-sha256": self.policy.dependency_lock_sha256
                },
            },
        }
        self.assertTrue(_valid_image(json.dumps(image), self.policy))
        image["Config"]["Env"].append("BUILD_TOKEN=should-not-exist")
        self.assertFalse(_valid_image(json.dumps(image), self.policy))

    def test_phase_report_parser_accepts_one_final_supervisor_marker(self):
        report = {"schema": "agentkit/local-phase-result-v1", "exit_code": 0}
        output = "ordinary pytest output\n" + _RESULT_MARKER + json.dumps(report)
        self.assertEqual(report, _phase_result_from_output(output))
        self.assertIsNone(
            _phase_result_from_output(
                output + "\n" + _RESULT_MARKER + json.dumps(report)
            )
        )

    def test_project_pytest_module_cannot_shadow_pinned_runner_import(self):
        poisoned = self.workspace / "pytest.py"
        poisoned.write_text("raise RuntimeError('project pytest shadowed runner')\n")
        self.assertLess(
            _PYTEST_CHILD.index("import pytest"),
            _PYTEST_CHILD.index("sys.path.append(root)"),
        )
        self.assertNotIn("sys.path.insert", _PYTEST_CHILD)
        code = (
            "import os,sys; import pytest; original=os.path.realpath(pytest.__file__); "
            "sys.path.append(sys.argv[1]); import pytest as loaded; "
            "assert loaded.__file__ and os.path.realpath(loaded.__file__)==original; "
            "assert os.path.commonpath([original,sys.argv[1]])!=sys.argv[1]"
        )
        subprocess.run(
            [sys.executable, "-c", code, str(self.workspace)],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_spawn_reimport_of_child_script_is_inert(self):
        import pytest

        namespace = {"__name__": "__mp_main__"}
        with (
            patch.object(
                pytest,
                "__file__",
                "/usr/local/lib/python3.12/site-packages/pytest/__init__.py",
            ),
            patch("os.path.commonpath", return_value="/tmp"),
            patch("builtins.open", side_effect=AssertionError("control read on spawn")),
            patch.object(
                pytest, "main", side_effect=AssertionError("pytest rerun on spawn")
            ),
        ):
            exec(compile(_PYTEST_CHILD, "agentkit-pytest-child.py", "exec"), namespace)
        self.assertTrue(callable(namespace.get("main")))

    def test_spawn_process_from_pytest_context_returns_without_recursive_suite(self):
        context = multiprocessing.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(target=_spawn_send, args=(sender, "spawn-ok"))
        process.start()
        sender.close()
        process.join(timeout=15)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
        receiver.close() if process.is_alive() else None
        self.assertFalse(process.is_alive(), "spawn child did not terminate")
        self.assertEqual(0, process.exitcode)
        # The pipe target is exercised in this host test; when the same test
        # runs inside the Docker pytest child, spawn re-imports _PYTEST_CHILD.
        self.assertEqual("spawn-ok", receiver.recv())
        receiver.close()

    def test_full_result_accounts_for_empty_and_module_skipped_test_files(self):
        empty = self.workspace / "tests" / "test_empty.py"
        empty.write_text("# intentionally contains no tests\n", encoding="utf-8")
        skipped = self.workspace / "tests" / "test_module_skipped.py"
        skipped.write_text(
            "import pytest\npytest.skip('fixture skip', allow_module_level=True)\n",
            encoding="utf-8",
        )
        self.data["snapshot_paths"].extend(
            ["tests/test_empty.py", "tests/test_module_skipped.py"]
        )
        self.data["allowed_write_paths"].extend(
            ["tests/test_empty.py", "tests/test_module_skipped.py"]
        )
        self.data["phases"]["full"]["test_files"].extend(
            ["tests/test_empty.py", "tests/test_module_skipped.py"]
        )
        self.manifest.write_text(json.dumps(self.data), encoding="utf-8")
        self.policy = LocalPhaseTestPolicy.from_file(self.manifest, self.workspace)
        plan = authorize_phase(self.policy, "full")
        freshness = verify_phase_freshness(self.policy, self.workspace, "full")
        nodeids = ["tests/test_worker.py::test_change"]
        files = [
            "tests/test_empty.py",
            "tests/test_module_skipped.py",
            "tests/test_worker.py",
        ]
        result = {
            "schema": "agentkit/local-phase-result-v1",
            "phase": "full",
            "exit_code": 0,
            "nodeids": nodeids,
            "nodeids_sha256": hashlib.sha256(
                json.dumps(nodeids, separators=(",", ":"), ensure_ascii=False).encode()
            ).hexdigest(),
            "files": files,
            "files_sha256": hashlib.sha256(
                json.dumps(files, separators=(",", ":"), ensure_ascii=False).encode()
            ).hexdigest(),
            "outcomes": {
                nodeids[0]: {
                    "outcome": "passed",
                    "exception_type": None,
                    "when": "call",
                }
            },
            "post_hashes": freshness["input_hashes"],
        }
        ok, reason, data = _valid_result(
            result, plan, self.policy, freshness, container_exit_code=0
        )
        self.assertTrue(ok, reason)
        self.assertEqual("ok", reason)
        self.assertEqual(3, data["collection"]["files_count"])
        self.assertIn("pytest_collectreport", _PYTEST_CHILD)

    def test_receipt_rejects_unknown_as_pass_and_digest_tampering(self):
        receipt = {
            "schema": "agentkit/local-phase-receipt-v1",
            "status": "unknown",
            "run_id": "d" * 32,
            "phase": "targeted",
            "reason": "transport_timeout",
            "exit_code": None,
            "outcome_source": "pytest_child_report",
            "policy_sha256": self.policy.sha256,
            "host_runner_sha256": self.policy.host_runner_sha256,
            "image_ref": self.policy.image_ref,
            "image_id": self.policy.image_id,
            "dependency_lock_sha256": self.policy.dependency_lock_sha256,
            "snapshot_sha256": hashlib.sha256(
                json.dumps(
                    [[path, "f" * 64] for path in self.policy.snapshot_paths],
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode()
            ).hexdigest(),
            "workspace_post_snapshot_sha256": "",
            "input_hashes": {path: "f" * 64 for path in self.policy.snapshot_paths},
            "collection": {},
            "outcomes": {},
            "scratch_post_hashes": {},
            "cleanup_confirmed": False,
            "duration_seconds": 1.0,
            "output": "",
        }
        receipt["receipt_sha256"] = hashlib.sha256(
            json.dumps(
                receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ).hexdigest()
        checked = validate_phase_receipt(receipt, self.policy, "d" * 32)
        self.assertEqual("unknown", checked["status"])
        receipt["reason"] = "ok"
        with self.assertRaises(ContractError):
            validate_phase_receipt(receipt, self.policy, "d" * 32)

    def test_mocked_docker_lifecycle_returns_bound_receipt_and_blocks_replay(self):
        run_id = "1" * 32
        plan = authorize_phase(self.policy, "targeted")
        freshness = verify_phase_freshness(self.policy, self.workspace, "targeted")
        nodeids = list(plan.nodeids)
        files = ["tests/test_worker.py"]
        result = {
            "schema": "agentkit/local-phase-result-v1",
            "phase": "targeted",
            "exit_code": 0,
            "nodeids": nodeids,
            "nodeids_sha256": hashlib.sha256(
                json.dumps(nodeids, separators=(",", ":"), ensure_ascii=False).encode()
            ).hexdigest(),
            "files": files,
            "files_sha256": hashlib.sha256(
                json.dumps(files, separators=(",", ":"), ensure_ascii=False).encode()
            ).hexdigest(),
            "outcomes": {
                nodeids[0]: {
                    "outcome": "passed",
                    "exception_type": None,
                    "when": "call",
                }
            },
            "post_hashes": freshness["input_hashes"],
        }
        container_id = "abcdef123456"
        calls = []
        create_args_seen = []
        inspected_payload = []

        def fake_runner(args, prompt, cwd, timeout, **kwargs):
            calls.append(args)
            if args[0:3] == ["docker", "image", "inspect"]:
                return (
                    0,
                    json.dumps(
                        {
                            "Id": self.policy.image_id,
                            "Config": {
                                "Env": [
                                    f"{key}={value}"
                                    for key, value in _IMAGE_ENV.items()
                                ],
                                "Labels": {
                                    "org.agentkit.test-lock-sha256": self.policy.dependency_lock_sha256
                                },
                            },
                        }
                    ),
                    "",
                )
            if args[0:2] == ["docker", "create"]:
                create_args_seen.extend(args)
                return 0, container_id, ""
            if args[0:3] == ["docker", "inspect", "--format"]:
                name = create_args_seen[create_args_seen.index("--name") + 1]
                mount = create_args_seen[create_args_seen.index("--mount") + 1]
                source = mount.split("source=", 1)[1].split(",target=", 1)[0]
                env = [
                    arg.removeprefix("--env=")
                    for arg in create_args_seen
                    if arg.startswith("--env=")
                ]
                image_index = create_args_seen.index(self.policy.image_ref)
                inspect = {
                    "Name": "/" + name,
                    "Image": self.policy.image_id,
                    "Config": {
                        "Image": self.policy.image_ref,
                        "User": "65534:65534",
                        "Entrypoint": ["/usr/bin/timeout"],
                        "WorkingDir": "/tmp",
                        "Cmd": create_args_seen[image_index + 1 :],
                        "Env": env,
                        "Labels": {"org.agentkit.phase-run": name},
                    },
                    "HostConfig": {
                        "NetworkMode": "none",
                        "ReadonlyRootfs": True,
                        "Privileged": False,
                        "CapDrop": ["ALL"],
                        "CapAdd": [],
                        "SecurityOpt": ["no-new-privileges"],
                        "Memory": self.policy.limits["memory_bytes"],
                        "MemorySwap": self.policy.limits["memory_swap_bytes"],
                        "NanoCpus": self.policy.limits["nano_cpus"],
                        "PidsLimit": self.policy.limits["pids"],
                        "Tmpfs": {
                            "/tmp": f"rw,noexec,nosuid,nodev,size={self.policy.limits['tmpfs_bytes']},mode=1777"
                        },
                        "Binds": [],
                        "Ulimits": [
                            {
                                "Name": "nofile",
                                "Soft": self.policy.limits["nofile"],
                                "Hard": self.policy.limits["nofile"],
                            }
                        ],
                    },
                    "Mounts": [
                        {
                            "Destination": "/source.tar",
                            "Type": "bind",
                            "RW": False,
                            "Source": source,
                        }
                    ],
                }
                inspected_payload.append(inspect)
                return 0, json.dumps(inspect), ""
            if args[0:3] == ["docker", "start", "--attach"]:
                return 0, "1 passed\n" + _RESULT_MARKER + json.dumps(result), ""
            if args[0:3] == ["docker", "rm", "--force"]:
                return 0, container_id, ""
            if args[0:3] == ["docker", "ps", "-a"]:
                return 0, "", ""
            raise AssertionError(f"Unexpected mocked Docker command: {args[1:3]}")

        result_dir = Path(self.temp.name) / "receipts"
        receipt = run_phase(
            self.policy,
            self.workspace,
            "targeted",
            run_id=run_id,
            timeout=30,
            runner=fake_runner,
            results_dir=result_dir,
        )
        self.assertEqual("passed", receipt["status"], receipt)
        self.assertTrue(receipt["cleanup_confirmed"])
        self.assertEqual(6, len(calls))
        inspected = inspected_payload[0]
        name = create_args_seen[create_args_seen.index("--name") + 1]
        source_archive = (
            create_args_seen[create_args_seen.index("--mount") + 1]
            .split("source=", 1)[1]
            .split(",target=", 1)[0]
        )
        inspected["HostConfig"]["Devices"] = [{"PathOnHost": "/dev/fake"}]
        self.assertFalse(
            _valid_container(json.dumps(inspected), self.policy, name, source_archive)
        )
        inspected["HostConfig"].pop("Devices")
        inspected["HostConfig"]["DeviceRequests"] = [{"Capabilities": [["gpu"]]}]
        self.assertFalse(
            _valid_container(json.dumps(inspected), self.policy, name, source_archive)
        )
        validate_phase_receipt(receipt, self.policy, run_id)
        with self.assertRaises(ContractError):
            run_phase(
                self.policy,
                self.workspace,
                "targeted",
                run_id=run_id,
                timeout=30,
                runner=fake_runner,
                results_dir=result_dir,
            )
        self.assertEqual(6, len(calls), "a duplicate attempt must not contact Docker")

    def test_timeout_is_unknown_and_locks_all_later_phases_for_run(self):
        run_id = "2" * 32
        calls = []

        def fake_runner(args, prompt, cwd, timeout, **kwargs):
            calls.append(args)
            if args[0:3] == ["docker", "image", "inspect"]:
                return (
                    0,
                    json.dumps(
                        {
                            "Id": self.policy.image_id,
                            "Config": {
                                "Env": [
                                    f"{key}={value}"
                                    for key, value in _IMAGE_ENV.items()
                                ],
                                "Labels": {
                                    "org.agentkit.test-lock-sha256": self.policy.dependency_lock_sha256
                                },
                            },
                        }
                    ),
                    "",
                )
            if args[0:2] == ["docker", "create"]:
                raise subprocess.TimeoutExpired(args, timeout)
            if args[0:3] == ["docker", "rm", "--force"]:
                return 0, "removed", ""
            if args[0:3] == ["docker", "ps", "-a"]:
                return 0, "", ""
            raise AssertionError(f"Unexpected mocked Docker command: {args[1:3]}")

        result_dir = Path(self.temp.name) / "unknown-receipts"
        receipt = run_phase(
            self.policy,
            self.workspace,
            "targeted",
            run_id=run_id,
            timeout=30,
            runner=fake_runner,
            results_dir=result_dir,
        )
        self.assertEqual("unknown", receipt["status"])
        self.assertEqual("transport_timeout", receipt["reason"])
        self.assertTrue(receipt["cleanup_confirmed"])
        validate_phase_receipt(receipt, self.policy, run_id)
        first_dispatch_count = len(calls)
        with self.assertRaises(ContractError):
            run_phase(
                self.policy,
                self.workspace,
                "full",
                run_id=run_id,
                timeout=30,
                runner=fake_runner,
                results_dir=result_dir,
            )
        self.assertEqual(
            first_dispatch_count,
            len(calls),
            "unknown outcome must lock later phases before Docker dispatch",
        )


if __name__ == "__main__":
    unittest.main()
