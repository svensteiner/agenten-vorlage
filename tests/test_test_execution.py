import hashlib
import json
import math
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from agentkit.contracts import ContractError
from agentkit.test_execution import (TestExecutionPolicy, _docker_args, _valid_container_inspect,
                                     _host_docker_runner, _pytest_outcomes,
                                     _safe_source_bytes, prepare_snapshot, run_isolated_tests,
                                     validate_test_receipt)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestExecutionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.tests = self.workspace / "tests"
        self.tests.mkdir()
        self.test_bytes = b"def test_ok():\n    assert 1 == 1\n"
        (self.tests / "test_ok.py").write_bytes(self.test_bytes)
        (self.workspace / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.lock_sha = "a" * 64
        self.image_id = "sha256:" + "b" * 64
        self.manifest = self.root / "operator-tests.json"
        self.write_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self, **overrides):
        value = {
            "version": 1,
            "image_ref": "python@sha256:" + "c" * 64,
            "image_id": self.image_id,
            "dependency_lock_sha256": self.lock_sha,
            "docker_transport": "native",
            "test_files": [{"path": "tests/test_ok.py", "sha256": digest(self.test_bytes)}],
            "support_files": [],
            "expected_test_count": 1,
            "snapshot_paths": ["app.py", "tests/test_ok.py"],
        }
        value.update(overrides)
        self.manifest.write_text(json.dumps(value), encoding="utf-8")
        return value

    def complete_fake_runner(self, policy, summary, *, cleanup_code=0, raise_timeout=False):
        state = {"mount": None, "create": None, "cleanup_calls": 0}

        def runner(args, prompt, cwd, timeout, **kwargs):
            if args[1] == "image":
                return 0, json.dumps({"Id": self.image_id, "Config": {"Labels": {
                    "org.agentkit.test-lock-sha256": self.lock_sha}}}), ""
            if args[1] == "create":
                state["create"] = args
                state["mount"] = args[args.index("--mount") + 1].split("source=", 1)[1].split(",target=", 1)[0]
                return 0, "d" * 64 + "\n", ""
            if args[1] == "inspect":
                return 0, json.dumps({
                    "Image": self.image_id,
                    "Config": {"Image": policy.image_ref, "User": "65534:65534",
                               "Entrypoint": ["/usr/bin/timeout"],
                               "Cmd": state["create"][state["create"].index(policy.image_ref) + 1:],
                               "Env": ["PYTEST_ADDOPTS=", "PYTEST_PLUGINS=", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1"],
                               "WorkingDir": "/workspace"},
                    "HostConfig": {"NetworkMode": "none", "ReadonlyRootfs": True, "Privileged": False,
                                   "CapDrop": ["ALL"], "CapAdd": [], "SecurityOpt": ["no-new-privileges"],
                                   "Memory": 134217728, "MemorySwap": 134217728, "NanoCpus": 1000000000,
                                   "PidsLimit": 32, "Binds": [],
                                   "Ulimits": [{"Name": "nofile", "Soft": 64, "Hard": 64}],
                                   "Tmpfs": {"/tmp": "rw,noexec,nosuid,nodev,size=16m,mode=1777"}},
                    "Mounts": [{"Destination": "/workspace", "RW": False, "Type": "bind",
                                "Source": state["mount"]}],
                }), ""
            if args[1] == "start":
                if raise_timeout:
                    raise subprocess.TimeoutExpired(args, timeout)
                return 0, summary, ""
            if args[1] == "rm":
                state["cleanup_calls"] += 1
                return cleanup_code, "", ""
            raise AssertionError(f"unexpected command: {args[1]}")

        return runner, state

    def test_manifest_is_exact_and_hash_binds_tests_image_dependencies(self):
        policy = TestExecutionPolicy.from_file(self.manifest)
        self.assertEqual(("tests/test_ok.py",), policy.test_paths)
        self.assertEqual(1, policy.expected_test_count)
        self.assertEqual(64, len(policy.sha256))
        self.write_manifest(image_ref="python@sha256:" + "d" * 64)
        self.assertNotEqual(policy.sha256, TestExecutionPolicy.from_file(self.manifest).sha256)

    def test_manifest_rejects_unknown_fields_and_unpinned_image(self):
        self.write_manifest(extra_docker_arg="--privileged")
        with self.assertRaises(ContractError):
            TestExecutionPolicy.from_file(self.manifest)

    def test_manifest_rejects_invalid_policy_fields_and_aliases(self):
        valid_test_hash = digest(self.test_bytes)
        invalid_values = [
            {"docker_transport": "arbitrary"},
            {"image_id": "not-an-image-id"},
            {"image_ref": "sha256:" + "d" * 64},
            {"dependency_lock_sha256": "bad"},
            {"test_files": []},
            {"test_files": [{"path": "tests/test_ok.py", "sha256": "bad"}]},
            {"test_files": [{"path": "tests/test_ok.py", "sha256": valid_test_hash},
                             {"path": "tests/test_ok.py", "sha256": valid_test_hash}]},
            {"support_files": [{"path": "tests/conftest.py"}]},
            {"support_files": [{"path": "tests/test_ok.py", "sha256": valid_test_hash}]},
            {"expected_test_count": False},
            {"snapshot_paths": []},
            {"snapshot_paths": ["app.py", "tests/test_ok.py", "tests/TEST_OK.py"]},
            {"snapshot_paths": ["app.py"]},
        ]
        for changes in invalid_values:
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.write_manifest(**changes)
                TestExecutionPolicy.from_file(self.manifest)

    def test_manifest_listed_files_are_prebounded_before_read(self):
        large = self.workspace / "large.py"
        large.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        self.write_manifest(snapshot_paths=["app.py", "large.py", "tests/test_ok.py"])
        policy = TestExecutionPolicy.from_file(self.manifest)
        with self.assertRaises(ContractError):
            prepare_snapshot(policy, self.workspace, self.root)

    def test_manifest_rejects_duplicate_keys_boolean_version_and_noncanonical_names(self):
        self.manifest.write_text('{"version":1,"version":1}', encoding="utf-8")
        with self.assertRaises(ContractError):
            TestExecutionPolicy.from_file(self.manifest)
        self.write_manifest(version=True)
        with self.assertRaises(ContractError):
            TestExecutionPolicy.from_file(self.manifest)
        self.write_manifest(snapshot_paths=["app.py", "tests/CON.py", "tests/test_ok.py"])
        with self.assertRaises(ContractError):
            TestExecutionPolicy.from_file(self.manifest)
        self.write_manifest(image_ref="python:latest")
        with self.assertRaises(ContractError):
            TestExecutionPolicy.from_file(self.manifest)

    def test_manifest_rejects_paths_outside_allowlist_and_secret_paths(self):
        self.write_manifest(snapshot_paths=["app.py", "tests/test_ok.py", "../secret"])
        with self.assertRaises(ContractError):
            TestExecutionPolicy.from_file(self.manifest)

    def test_manifest_pins_support_files_and_expected_collection_count(self):
        support = b"# frozen fixture support\n"
        (self.tests / "conftest.py").write_bytes(support)
        self.write_manifest(
            support_files=[{"path": "tests/conftest.py", "sha256": digest(support)}],
            expected_test_count=2,
            snapshot_paths=["app.py", "tests/conftest.py", "tests/test_ok.py"],
        )
        policy = TestExecutionPolicy.from_file(self.manifest)
        self.assertEqual(("tests/conftest.py",), policy.support_paths)
        self.assertEqual(2, policy.expected_test_count)
        snapshot, _ = prepare_snapshot(policy, self.workspace, self.root)
        self.assertEqual(support, (snapshot / "tests/conftest.py").read_bytes())
        (self.tests / "conftest.py").write_bytes(b"changed")
        with self.assertRaises(ContractError):
            prepare_snapshot(policy, self.workspace, self.root)
        self.write_manifest(expected_test_count=True)
        with self.assertRaises(ContractError):
            TestExecutionPolicy.from_file(self.manifest)

    def test_manifest_allows_curated_security_related_python_modules(self):
        self.write_manifest(snapshot_paths=["app.py", "provider_credentials.py",
                                            "tests/test_token_budget.py", "tests/test_ok.py"])
        policy = TestExecutionPolicy.from_file(self.manifest)
        self.assertIn("provider_credentials.py", policy.snapshot_paths)
        self.assertIn("tests/test_token_budget.py", policy.snapshot_paths)
        self.write_manifest(snapshot_paths=["app.py", "tests/test_ok.py", ".env"])
        with self.assertRaises(ContractError):
            TestExecutionPolicy.from_file(self.manifest)

    def test_snapshot_contains_only_curated_bytes_and_pinned_tests(self):
        policy = TestExecutionPolicy.from_file(self.manifest)
        snapshot, snapshot_sha = prepare_snapshot(policy, self.workspace, self.root)
        self.assertEqual({"app.py", "tests/test_ok.py"}, {
            item.relative_to(snapshot).as_posix() for item in snapshot.rglob("*") if item.is_file()
        })
        self.assertEqual(self.test_bytes, (snapshot / "tests/test_ok.py").read_bytes())
        self.assertEqual(64, len(snapshot_sha))
        (self.tests / "test_ok.py").write_bytes(b"changed")
        with self.assertRaises(ContractError):
            prepare_snapshot(policy, self.workspace, self.root)

    def test_symlink_is_rejected_before_copy(self):
        self.write_manifest(snapshot_paths=["app.py", "linked.py", "tests/test_ok.py"])
        policy = TestExecutionPolicy.from_file(self.manifest)
        real_is_symlink = Path.is_symlink
        with patch.object(Path, "is_symlink", autospec=True,
                          side_effect=lambda item: item.name == "linked.py" or real_is_symlink(item)):
            with self.assertRaises(ContractError):
                prepare_snapshot(policy, self.workspace, self.root)

    def _assert_source_symlink_swap_never_returns_outside_bytes(self, *, parent: bool):
        outside = self.root / "outside"
        outside.mkdir()
        outside_file = outside / "test_ok.py"
        outside_file.write_bytes(b"outside-secret-payload")
        target = self.tests / "test_ok.py"
        target.write_bytes(b"inside")
        from agentkit.test_execution import _open_source_handle
        real_open = _open_source_handle

        def swap_then_open(workspace, path, relative):
            if parent:
                moved = self.workspace / "tests-original"
                self.tests.rename(moved)
                self.tests.symlink_to(outside, target_is_directory=True)
                try:
                    return real_open(workspace, path, relative)
                finally:
                    self.tests.unlink()
                    moved.rename(self.tests)
            moved = self.tests / "test_ok.original"
            target.rename(moved)
            target.symlink_to(outside_file)
            try:
                return real_open(workspace, path, relative)
            finally:
                target.unlink()
                moved.rename(target)

        with patch("agentkit.test_execution._open_source_handle", side_effect=swap_then_open):
            try:
                data = _safe_source_bytes(self.workspace, "tests/test_ok.py", 1024)
            except ContractError:
                return
        self.assertNotEqual(b"outside-secret-payload", data)
        self.fail("snapshot read returned bytes through a raced symlink")

    def test_snapshot_read_rejects_final_component_symlink_swap(self):
        self._assert_source_symlink_swap_never_returns_outside_bytes(parent=False)

    def test_snapshot_read_rejects_parent_component_symlink_swap(self):
        self._assert_source_symlink_swap_never_returns_outside_bytes(parent=True)

    def test_wrong_image_inspection_never_starts_container_and_cleans_it(self):
        policy = TestExecutionPolicy.from_file(self.manifest)
        calls = []

        def runner(args, prompt, cwd, timeout, **kwargs):
            calls.append(args)
            if args[1] == "image":
                return 0, json.dumps({"Id": "sha256:" + "x" * 64, "Config": {"Labels": {
                    "org.agentkit.test-lock-sha256": self.lock_sha}}}), ""
            if args[1] == "create":
                return 0, "d" * 64 + "\n", ""
            if args[1] == "inspect":
                return 0, json.dumps({"Image": self.image_id, "Config": {"Image": policy.image_ref,
                    "User": "65534:65534"}, "HostConfig": {}}), ""
            if args[1] == "rm":
                return 0, "", ""
            raise AssertionError(f"unexpected command: {args[1]}")

        result = run_isolated_tests(policy, self.workspace, run_id="a" * 32,
                                    timeout=10, runner=runner, temp_root=self.root)
        self.assertEqual("failed", result["status"])
        self.assertNotIn("start", [call[1] for call in calls])
        self.assertNotIn("create", [call[1] for call in calls])

    def test_wrong_dependency_lock_label_never_creates_container(self):
        policy = TestExecutionPolicy.from_file(self.manifest)
        calls = []

        def runner(args, prompt, cwd, timeout, **kwargs):
            calls.append(args)
            if args[1] == "image":
                return 0, json.dumps({"Id": self.image_id, "Config": {"Labels": {
                    "org.agentkit.test-lock-sha256": "f" * 64}}}), ""
            raise AssertionError(f"unexpected command: {args[1]}")

        result = run_isolated_tests(policy, self.workspace, run_id="a" * 32,
                                    timeout=10, runner=runner, temp_root=self.root)
        self.assertEqual("failed", result["status"])
        self.assertEqual("pinned_image_unavailable_or_mismatch", result["reason"])
        self.assertEqual(["image"], [call[1] for call in calls])

    def test_all_skipped_or_deselected_summary_never_passes(self):
        policy = TestExecutionPolicy.from_file(self.manifest)
        for summary, expected_reason in (("1 skipped in 0.1s", "pytest_outcome_summary_rejected"),
                                         ("1 passed, 1 deselected in 0.1s", "pytest_outcome_count_mismatch")):
            with self.subTest(summary=summary):
                runner, _ = self.complete_fake_runner(policy, summary)
                result = run_isolated_tests(policy, self.workspace, run_id="a" * 32,
                                            timeout=10, runner=runner, temp_root=self.root)
                self.assertEqual("failed", result["status"])
                self.assertEqual(expected_reason, result["reason"])

    def test_start_timeout_and_double_cleanup_failure_are_recorded_closed(self):
        policy = TestExecutionPolicy.from_file(self.manifest)
        runner, state = self.complete_fake_runner(policy, "", raise_timeout=True)
        timed_out = run_isolated_tests(policy, self.workspace, run_id="a" * 32,
                                       timeout=10, runner=runner, temp_root=self.root)
        self.assertEqual("timeout", timed_out["status"])
        self.assertTrue(timed_out["cleanup_confirmed"])
        self.assertEqual(1, state["cleanup_calls"])

        runner, state = self.complete_fake_runner(policy, "1 passed in 0.1s", cleanup_code=1)
        cleanup_failed = run_isolated_tests(policy, self.workspace, run_id="b" * 32,
                                            timeout=10, runner=runner, temp_root=self.root)
        self.assertEqual("failed", cleanup_failed["status"])
        self.assertEqual("container_cleanup_failed", cleanup_failed["reason"])
        self.assertFalse(cleanup_failed["cleanup_confirmed"])
        self.assertEqual(2, state["cleanup_calls"])

    def test_nonfinite_timeout_is_rejected_before_runner(self):
        policy = TestExecutionPolicy.from_file(self.manifest)
        for timeout in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(timeout=timeout), self.assertRaises(ContractError):
                run_isolated_tests(policy, self.workspace, run_id="a" * 32,
                                    timeout=timeout, runner=lambda *args: self.fail("runner must not run"))

    def test_success_receipt_is_host_created_and_reports_exact_snapshot_and_suite(self):
        policy = TestExecutionPolicy.from_file(self.manifest)
        calls = []
        mount_source = None
        create_args = []

        def runner(args, prompt, cwd, timeout, **kwargs):
            calls.append(args)
            if args[1] == "image":
                return 0, json.dumps({"Id": self.image_id, "Config": {"Labels": {
                    "org.agentkit.test-lock-sha256": self.lock_sha}}}), ""
            if args[1] == "create":
                nonlocal mount_source
                nonlocal create_args
                self.assertIn("--network=none", args)
                self.assertIn("--read-only", args)
                self.assertIn("--cap-drop=ALL", args)
                self.assertIn("target=/workspace,readonly", " ".join(args))
                mount_source = args[args.index("--mount") + 1].split("source=", 1)[1].split(",target=", 1)[0]
                create_args = args
                return 0, "d" * 64 + "\n", ""
            if args[1] == "inspect":
                return 0, json.dumps({
                    "Image": self.image_id,
                    "Config": {"Image": policy.image_ref, "User": "65534:65534",
                               "Entrypoint": ["/usr/bin/timeout"],
                               "Cmd": create_args[create_args.index(policy.image_ref) + 1:],
                               "Env": ["PYTEST_ADDOPTS=", "PYTEST_PLUGINS=", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1"],
                               "WorkingDir": "/workspace"},
                    "HostConfig": {
                        "NetworkMode": "none", "ReadonlyRootfs": True, "Privileged": False,
                        "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"],
                        "Memory": 134217728, "MemorySwap": 134217728, "NanoCpus": 1000000000,
                        "PidsLimit": 32, "Binds": None,
                        "Ulimits": [{"Name": "nofile", "Soft": 64, "Hard": 64}],
                        "Tmpfs": {"/tmp": "rw,noexec,nosuid,nodev,size=16m,mode=1777"},
                    },
                    "Mounts": [{"Destination": "/workspace", "RW": False, "Type": "bind",
                                "Source": mount_source}],
                }), ""
            if args[1] == "start":
                return 0, "1 passed\n", ""
            if args[1] == "rm":
                return 0, "", ""
            raise AssertionError(f"unexpected command: {args[1]}")

        result = run_isolated_tests(policy, self.workspace, run_id="a" * 32,
                                    timeout=10, runner=runner, temp_root=self.root)
        self.assertEqual("passed", result["status"], result)
        self.assertEqual(policy.sha256, result["policy_sha256"])
        self.assertEqual(["tests/test_ok.py"], result["test_paths"])
        self.assertEqual(64, len(result["snapshot_sha256"]))
        validate_test_receipt(result, policy, "a" * 32)
        for field, value in (("duration_seconds", math.nan), ("cleanup_confirmed", False),
                             ("expected_test_count", 2)):
            mutated = dict(result)
            mutated[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_test_receipt(mutated, policy, "a" * 32)
        self.assertEqual({"passed": 1, "failed": 0, "errors": 0, "skipped": 0,
                          "xfailed": 0, "xpassed": 0, "deselected": 0}, result["test_outcomes"])
        self.assertIn("start", [call[1] for call in calls])
        self.assertIn("rm", [call[1] for call in calls])

    def test_default_runner_uses_host_transport_wrapper(self):
        policy = TestExecutionPolicy.from_file(self.manifest)
        seen = []

        def wrapped(args, prompt, cwd, timeout, **kwargs):
            seen.append(args)
            return 1, "", ""

        with patch("agentkit.backends._process_result", return_value=(1, "", "")), \
             patch("agentkit.test_execution._host_docker_runner", return_value=wrapped) as host_runner:
            result = run_isolated_tests(policy, self.workspace, run_id="a" * 32,
                                        timeout=10, temp_root=self.root)
        host_runner.assert_called_once()
        self.assertEqual("failed", result["status"])
        self.assertEqual("docker", seen[0][0])

    def test_docker_timeout_is_pid1_deadline_and_inspection_binds_it(self):
        policy = TestExecutionPolicy.from_file(self.manifest)
        args = _docker_args(policy, self.root, "agentkit-test-fixed", 10)
        self.assertIn("--entrypoint=/usr/bin/timeout", args)
        self.assertIn("--kill-after=2", args)
        self.assertTrue(any("import pytest" in arg for arg in args))
        self.assertNotIn("--init", args)
        self.assertEqual("/usr/bin/timeout", args[args.index("--entrypoint=/usr/bin/timeout") + 0].split("=",1)[1])
        inspect = {
            "Image": self.image_id,
            "Config": {"Image": policy.image_ref, "User": "65534:65534",
                       "Entrypoint": ["/usr/bin/timeout"],
                       "Cmd": ["--signal=TERM", "--kill-after=2", "10", "/usr/local/bin/python",
                               "-I", "-B", "-c",
                               "import sys; sys.path[:0] = ['/workspace', '/workspace/src']; import pytest; raise SystemExit(pytest.main(['-q', '-c', '/dev/null', '-p', 'no:cacheprovider', '--', *sys.argv[1:]]))",
                               "tests/test_ok.py"],
                       "Env": ["PYTEST_ADDOPTS=", "PYTEST_PLUGINS=", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1"],
                       "WorkingDir": "/workspace"},
            "HostConfig": {"NetworkMode": "none", "ReadonlyRootfs": True, "Privileged": False,
                           "CapDrop": ["ALL"], "CapAdd": [], "SecurityOpt": ["no-new-privileges"],
                           "Memory": 134217728, "MemorySwap": 134217728, "NanoCpus": 1000000000,
                           "PidsLimit": 32, "Binds": [],
                           "Ulimits": [{"Name": "nofile", "Soft": 64, "Hard": 64}],
                           "Tmpfs": {"/tmp": "rw,noexec,nosuid,nodev,size=16m,mode=1777"}},
            "Mounts": [{"Destination": "/workspace", "RW": False, "Type": "bind",
                        "Source": str(self.root.resolve()).replace("\\", "/")}],
        }
        self.assertTrue(_valid_container_inspect(json.dumps(inspect), policy, self.root, timeout_seconds=10))
        inspect["Config"]["Entrypoint"] = ["/bin/sh"]
        self.assertFalse(_valid_container_inspect(json.dumps(inspect), policy, self.root, timeout_seconds=10))

    def test_inspection_rejects_privilege_network_mount_and_env_drift(self):
        policy = TestExecutionPolicy.from_file(self.manifest)
        good = {
            "Image": self.image_id,
            "Config": {"Image": policy.image_ref, "User": "65534:65534",
                       "Entrypoint": ["/usr/bin/timeout"],
                       "Cmd": ["--signal=TERM", "--kill-after=2", "10", "/usr/local/bin/python", "-I", "-B", "-c",
                               "import sys; sys.path[:0] = ['/workspace', '/workspace/src']; import pytest; raise SystemExit(pytest.main(['-q', '-c', '/dev/null', '-p', 'no:cacheprovider', '--', *sys.argv[1:]]))",
                               "tests/test_ok.py"],
                       "Env": ["PYTEST_ADDOPTS=", "PYTEST_PLUGINS=", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1"],
                       "WorkingDir": "/workspace"},
            "HostConfig": {"NetworkMode": "none", "ReadonlyRootfs": True, "Privileged": False,
                           "CapDrop": ["ALL"], "CapAdd": [], "SecurityOpt": ["no-new-privileges"],
                           "Memory": 134217728, "MemorySwap": 134217728, "NanoCpus": 1000000000,
                           "PidsLimit": 32, "Binds": [],
                           "Ulimits": [{"Name": "nofile", "Soft": 64, "Hard": 64}],
                           "Tmpfs": {"/tmp": "rw,noexec,nosuid,nodev,size=16m,mode=1777"}},
            "Mounts": [{"Destination": "/workspace", "RW": False, "Type": "bind",
                        "Source": str(self.root.resolve()).replace("\\", "/")}],
        }
        changes = [
            ("HostConfig", "Privileged", True),
            ("HostConfig", "NetworkMode", "bridge"),
            ("HostConfig", "ReadonlyRootfs", False),
            ("HostConfig", "CapAdd", ["SYS_ADMIN"]),
            ("HostConfig", "SecurityOpt", ["no-new-privileges=false"]),
            ("Config", "Env", ["PYTEST_ADDOPTS=", "PYTEST_PLUGINS=", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", "PYTEST_ADDOPTS=-k anything"]),
        ]
        self.assertTrue(_valid_container_inspect(json.dumps(good), policy, self.root, timeout_seconds=10))
        for section, key, value in changes:
            altered = json.loads(json.dumps(good))
            altered[section][key] = value
            with self.subTest(section=section, key=key):
                self.assertFalse(_valid_container_inspect(json.dumps(altered), policy, self.root, timeout_seconds=10))

    def test_native_transport_cleans_docker_environment(self):
        self.write_manifest(docker_transport="native")
        policy = TestExecutionPolicy.from_file(self.manifest)
        captured = {}

        def base(args, prompt, cwd, timeout, **kwargs):
            captured.update({"args": args, "env": kwargs.get("env", {})})
            return 0, "ok", ""

        with tempfile.TemporaryDirectory() as config:
            with patch("agentkit.test_execution.shutil.which", return_value="docker.exe"):
                runner = _host_docker_runner(policy, Path(config), base)
                self.assertEqual((0, "ok", ""), runner(["docker", "version"], "", self.workspace, 5))
        self.assertEqual("docker.exe", captured["args"][0])
        self.assertIn("DOCKER_CONFIG", captured["env"])
        for name in ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH", "WSLENV"):
            self.assertNotIn(name, captured["env"])

    def test_summary_counts_cover_skips_and_reject_deselection_indicators(self):
        self.assertEqual({"passed": 2, "failed": 0, "errors": 0, "skipped": 3,
                          "xfailed": 1, "xpassed": 0, "deselected": 0},
                         _pytest_outcomes("2 passed, 3 skipped, 1 xfailed in 0.3s"))
        self.assertEqual(2, _pytest_outcomes("1 passed, 1 deselected in 0.1s")["deselected"] +
                         _pytest_outcomes("1 passed, 1 deselected in 0.1s")["passed"])
        self.assertEqual(0, sum(_pytest_outcomes("no tests ran in 0.0s").values()))


if __name__ == "__main__":
    unittest.main()
