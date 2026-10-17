from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.contracts import ContractError
from agentkit.scaffold import create
from agentkit.approvals import action_digest, replay_action_digest, workspace_fingerprint
from cockpit.execution_profiles import ExecutionProfileRegistry
from cockpit.server import JobManager


class ExecutionProfileRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agent = create(self.root / "agents" / "editor", "developer", "editor", "Example")
        self.workspace = self.root / "project"
        self.workspace.mkdir()
        self.manager = JobManager(template_root=self.root, agent_roots=(self.root / "agents",),
                                  generated_root=self.root / "agents", state_dir=self.root / "state")
        self.profile_path = self.root / "execution-profiles.json"

    def tearDown(self):
        for job in self.manager.recent(1000):
            if job.thread:
                job.thread.join(5)
        self.temp.cleanup()

    def _profile(self, **overrides):
        item = {
            "id": "editor-safe", "label": "Editor · allowlisted files",
            "agent": str(self.agent), "workspace": str(self.workspace), "backend": "demo",
            "write_paths": ["notes.md"], "test_manifest": None, "host_autonomous": False,
        }
        item.update(overrides)
        return {"version": 1, "profiles": [item]}

    def _write(self, data=None):
        self.profile_path.write_text(json.dumps(data or self._profile()), encoding="utf-8")
        return self.profile_path

    def _configured_manager(self, data=None):
        self._write(data)
        return JobManager(template_root=self.root, agent_roots=(self.root / "agents",),
                          generated_root=self.root / "agents", state_dir=self.root / "profile-state",
                          execution_profiles_path=self.profile_path)

    def test_loads_concrete_bound_profile_with_safe_ui_metadata(self):
        registry = ExecutionProfileRegistry(self.manager, self._write())
        profile = registry.resolve("editor-safe", str(self.agent), str(self.workspace), "demo")
        self.assertEqual(profile.agent, self.manager._agent_reference(self.manager._agent_path(str(self.agent))))
        self.assertEqual(profile.workspace, self.manager._workspace_reference(self.manager._workspace_path(str(self.workspace))))
        self.assertEqual(profile.backend, "demo")
        self.assertEqual(profile.write_policy.paths, ("notes.md",))
        self.assertFalse(profile.host_autonomous)
        self.assertRegex(profile.sha256, r"^[0-9a-f]{64}$")
        metadata = registry.options_for(str(self.agent), str(self.workspace), "demo")
        self.assertEqual(len(metadata), 1)
        self.assertEqual(metadata[0]["id"], "editor-safe")
        self.assertNotIn("test_manifest", json.dumps(metadata))
        self.assertNotIn("write_policy_sha256", metadata[0])
        with self.assertRaises((AttributeError, TypeError)):
            profile.host_autonomous = True

    def test_rejects_agent_workspace_backend_or_digest_swap(self):
        registry = ExecutionProfileRegistry(self.manager, self._write())
        for agent, workspace, backend, digest in (
            (str(self.root / "agents" / "other"), str(self.workspace), "demo", None),
            (str(self.agent), str(self.root / "other"), "demo", None),
            (str(self.agent), str(self.workspace), "codex", None),
            (str(self.agent), str(self.workspace), "demo", "0" * 64),
        ):
            with self.subTest(agent=agent, workspace=workspace, backend=backend), self.assertRaises(ContractError):
                registry.resolve("editor-safe", agent, workspace, backend, expected_digest=digest)

    def test_digest_changes_with_concrete_policy_binding(self):
        first = ExecutionProfileRegistry(self.manager, self._write()).get("editor-safe")
        second_data = self._profile()
        second_data["profiles"][0]["write_paths"] = ["other.md"]
        second = ExecutionProfileRegistry(self.manager, self._write(second_data)).get("editor-safe")
        self.assertNotEqual(first.sha256, second.sha256)

    def test_rejects_client_shaped_fields_duplicate_ids_and_autonomy_without_allowlist(self):
        for bad in (
            self._profile(policy_file="attacker.json"),
            {"version": 1, "profiles": [self._profile()["profiles"][0], self._profile()["profiles"][0]]},
            self._profile(write_paths=[], host_autonomous=True),
        ):
            with self.subTest(profile=bad), self.assertRaises(ContractError):
                ExecutionProfileRegistry(self.manager, self._write(bad))

    def test_autonomous_profile_requires_both_write_allowlist_and_pinned_tests(self):
        for profile in (
            self._profile(test_manifest=None, host_autonomous=True),
            self._profile(write_paths=[], host_autonomous=True),
        ):
            with self.subTest(profile=profile), self.assertRaisesRegex(ContractError, "pinned host test suite"):
                ExecutionProfileRegistry(self.manager, self._write(profile))

    def test_autonomous_profile_can_bind_write_allowlist_and_fixed_test_policy(self):
        manifest = self.root / "tests.json"
        image = "sha256:" + "a" * 64
        manifest.write_text(json.dumps({
            "version": 1, "image_ref": image, "image_id": image,
            "dependency_lock_sha256": "b" * 64, "docker_transport": "native",
            "test_files": [{"path": "tests/test_smoke.py", "sha256": "c" * 64}],
            "support_files": [], "expected_test_count": 1,
            "snapshot_paths": ["tests/test_smoke.py"],
        }), encoding="utf-8")
        row = self._profile(backend="codex", test_manifest=str(manifest), host_autonomous=True)["profiles"][0]
        profile_path = self.root / "autonomous.json"
        profile_path.write_text(json.dumps({"version": 1, "profiles": [row]}), encoding="utf-8")
        profile = ExecutionProfileRegistry(self.manager, profile_path).get("editor-safe")
        self.assertTrue(profile.host_autonomous)
        self.assertEqual(profile.write_policy.paths, ("notes.md",))
        self.assertEqual(profile.test_execution_policy.expected_test_count, 1)

    def test_job_start_accepts_only_id_and_binds_approval_policy_for_idempotency(self):
        manager = self._configured_manager()
        payload = {"agent": str(self.agent), "workspace": str(self.workspace), "backend": "demo",
                   "task": "bounded", "request_id": "a" * 32,
                   "execution_profile_id": "editor-safe"}
        with patch.object(manager, "_launch"):
            job = manager.start(payload)
        self.assertEqual("editor-safe", job.payload["execution_profile_id"])
        self.assertRegex(job.payload["execution_profile_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(job.payload["require_approvals"])
        self.assertEqual("editor-safe", job.public()["execution_profile_id"])
        self.assertTrue(job.public()["require_approvals"])
        with self.assertRaises(ContractError):
            manager.start({**payload, "write_paths": ["anything.md"]})
        with self.assertRaises(ContractError):
            manager.start({**payload, "require_approvals": False})
        with self.assertRaises(ContractError):
            manager.start({**payload, "workspace": str(self.root / "other")})

    def test_profile_change_stops_resume_before_worker_reservation(self):
        manager = self._configured_manager()
        payload = {"agent": str(self.agent), "workspace": str(self.workspace), "backend": "demo",
                   "task": "bounded", "request_id": "b" * 32,
                   "execution_profile_id": "editor-safe"}
        with patch.object(manager, "_launch"):
            job = manager.start(payload)
        job.status = "blocked"
        manager._persist(job)
        changed = self._profile()
        changed["profiles"][0]["write_paths"] = ["different.md"]
        self._write(changed)
        manager.execution_profile_registry = ExecutionProfileRegistry(manager, self.profile_path)
        with patch.object(manager, "_reserve_worker", side_effect=AssertionError("reserved")):
            with self.assertRaisesRegex(ContractError, "changed"):
                manager.resume(job.job_id, "continue", True)

    def test_conversation_profile_is_bound_and_client_cannot_supply_policy(self):
        from cockpit.conversations import Conversations

        manager = self._configured_manager()
        conversations = Conversations(manager)
        base = {"agent": str(self.agent), "workspace": str(self.workspace), "backend": "demo",
                "request_id": "c" * 32, "title": "profile", "execution_profile_id": "editor-safe"}
        created = conversations.create(base)
        self.assertEqual("editor-safe", created["execution_profile"]["id"])
        self.assertEqual(manager._workspace_reference(manager._workspace_path(str(self.workspace))),
                         created["execution_profile"]["workspace"])
        with self.assertRaises(ContractError):
            conversations.create({**base, "write_paths": ["forged.md"]})
        with self.assertRaises(ContractError):
            conversations.create({**base, "require_approvals": False})
        with patch.object(manager, "_launch"):
            conversations.send(created["id"], {"request_id": "d" * 32, "content": "do bounded work"})
        job = manager.get("d" * 32)
        self.assertEqual("editor-safe", job.payload["execution_profile_id"])
        self.assertEqual(created["execution_profile"]["sha256"], job.payload["execution_profile_sha256"])

    def test_public_mode_rejects_execution_profile_registry(self):
        public = JobManager(template_root=self.root, agent_roots=(self.root / "agents",),
                            generated_root=self.root / "agents", state_dir=self.root / "public-state",
                            public_mode=True, workspace_root=self.root / "public-workspaces")
        with self.assertRaises(ContractError):
            ExecutionProfileRegistry(public, self._write())

    def test_autonomous_write_test_review_flow_uses_real_engine_gates(self):
        manifest = self.root / "tests.json"
        image = "sha256:" + "a" * 64
        manifest.write_text(json.dumps({
            "version": 1, "image_ref": "python@sha256:" + "a" * 64, "image_id": image,
            "dependency_lock_sha256": "b" * 64, "docker_transport": "native",
            "test_files": [{"path": "tests/test_smoke.py", "sha256": "c" * 64}],
            "support_files": [], "expected_test_count": 1,
            "snapshot_paths": ["tests/test_smoke.py"],
        }), encoding="utf-8")
        profile_path = self.root / "autonomous.json"
        profile_path.write_text(json.dumps({"version": 1, "profiles": [self._profile(
            backend="codex", test_manifest=str(manifest), host_autonomous=True
        )["profiles"][0]]}), encoding="utf-8")
        manager = JobManager(template_root=self.root, agent_roots=(self.root / "agents",),
                             generated_root=self.root / "agents", state_dir=self.root / "run-state",
                             execution_profiles_path=profile_path)

        class FakeBackend:
            name = "codex"
            supports_action_approvals = True
            supports_write_policy = True
            supports_isolated_tests = True
            approval_identity = "fixture"

            def __init__(self, stale_after_test=False):
                self.stale_after_test = stale_after_test

            def decide(self, context, timeout):
                history = context["history"]
                if not history:
                    return {"action": "delegate", "role": "developer", "skills": [], "task": "edit and test", "reason": "fixture"}
                if history[-1]["decision"].get("role") == "developer":
                    return {"action": "delegate", "role": "reviewer", "skills": [], "task": "review", "reason": "fixture"}
                if history[-1]["decision"].get("completion_rejected"):
                    return {"action": "blocked", "role": "", "skills": [], "task": "stale test receipt", "reason": "fixture"}
                return {"action": "finish", "role": "", "skills": [], "task": "done", "reason": "fixture"}

            def execute(self, decision, context, timeout):
                if decision["role"] == "developer":
                    policy = context["write_policy"]
                    test_policy = context["test_execution_policy"]
                    self_outer.assertFalse(context["require_approvals"])
                    self_outer.assertEqual(("notes.md",), policy.paths)
                    path = Path(context["workspace"]) / "notes.md"
                    context["write_policy"].authorize_action(Path(context["workspace"]), "write_file", {"path": "notes.md"})
                    path.write_text("bounded edit", encoding="utf-8")
                    def record_write():
                        context["record_completed_action"]({
                            "kind": "completed_action", "tool": "write_file",
                            "action_sha256": action_digest("write_file", {"path": "notes.md"}),
                            "replay_sha256": replay_action_digest("write_file", {"path": "notes.md"}, Path(context["workspace"])),
                            "post_workspace_fingerprint": workspace_fingerprint(Path(context["workspace"])),
                        })
                    record_write()
                    self_outer.assertEqual("python@sha256:" + "a" * 64, test_policy.image_ref)
                    context["begin_test_execution"]()
                    context["record_test_execution"]({
                        "status": "passed", "run_id": context["run_id"], "reason": "ok", "exit_code": 0,
                        "policy_sha256": test_policy.sha256, "test_manifest_sha256": test_policy.sha256,
                        "test_paths": list(test_policy.test_paths), "expected_test_count": test_policy.expected_test_count,
                        "test_outcomes": {"passed": 1, "failed": 0, "errors": 0, "skipped": 0,
                                          "xfailed": 0, "xpassed": 0, "deselected": 0},
                        "image_ref": test_policy.image_ref, "image_id": test_policy.image_id,
                        "dependency_lock_sha256": test_policy.dependency_lock_sha256,
                        "snapshot_sha256": "d" * 64,
                        "workspace_fingerprint": workspace_fingerprint(Path(context["workspace"])),
                        "duration_seconds": 0.1, "output": "1 passed", "cleanup_confirmed": True,
                    })
                    if self.stale_after_test:
                        path.write_text("changed after test", encoding="utf-8")
                        record_write()
                return {"status": "success", "summary": "reviewed fixture", "artifacts": [],
                        "evidence": ["reviewed"], "next_actions": []}

        self_outer = self
        for stale in (False, True):
            backend = FakeBackend(stale_after_test=stale)
            payload = {"agent": str(self.agent), "workspace": str(self.workspace), "backend": "codex",
                       "task": "bounded edit, test, review", "request_id": ("e" if stale else "f") * 32,
                       "execution_profile_id": "editor-safe"}
            with patch.object(manager, "_launch"), patch("cockpit.server.CodexBackend", return_value=backend):
                job = manager.start(payload)
                manager._run(job)
            if stale:
                self.assertNotEqual("completed", job.status)
                self.assertIsNone((job.result or {}).get("latest_test_execution_receipt"))
            else:
                self.assertEqual("completed", job.status)
                self.assertTrue(job.result["reviewed"])
                self.assertEqual("passed", job.result["latest_test_execution_receipt"]["status"])
                self.assertEqual(1, job.result["test_execution_runs"])


if __name__ == "__main__":
    unittest.main()
