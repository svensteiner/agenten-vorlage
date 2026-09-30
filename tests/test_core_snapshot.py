import json
import tempfile
import unittest
from pathlib import Path

from agentkit.backends import DemoBackend
from agentkit.contracts import ContractError
from agentkit.engine import Engine
from agentkit.catalog import Catalog
from agentkit.scaffold import create


def decision(action="delegate", role="developer"):
    return {"action": action, "role": role if action == "delegate" else "", "skills": [], "task": "Bounded task", "reason": "Observed"}


class SnapshotBackend:
    name = "snapshot-test"

    def __init__(self, choices, on_execute=None):
        self.choices = iter(choices)
        self.contexts = []
        self.on_execute = on_execute

    def decide(self, context, timeout):
        self.contexts.append(dict(context))
        return next(self.choices)

    def execute(self, choice, context, timeout):
        if self.on_execute:
            self.on_execute(self.calls if hasattr(self, "calls") else 0)
        self.calls = getattr(self, "calls", 0) + 1
        Path(context["workspace"], "snapshot-artifact.txt").write_text("ok", encoding="utf-8")
        return {"status": "success", "summary": "ok", "artifacts": ["snapshot-artifact.txt"], "evidence": ["verified"], "next_actions": []}


class CoreSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agent = create(self.root / "agent", "developer", "assistant", "Company")
        self.workspace = self.agent / "workspace"

    def tearDown(self):
        self.temp.cleanup()

    def test_snapshot_survives_soul_edit_during_worker_and_resume(self):
        soul = self.agent / "SOUL.md"
        original = soul.read_text(encoding="utf-8")
        original_core = Catalog(self.agent).core()
        backend = SnapshotBackend([decision(), decision(role="reviewer"), decision("finish")],
                                  lambda index: (self.agent / "SOUL.md").write_text("CHANGED DURING WORK", encoding="utf-8") if index == 0 else None)
        state = Engine(self.agent, self.workspace, backend).run("snapshot")
        self.assertEqual("completed", state["status"])
        self.assertEqual(original_core, backend.contexts[0]["core"])
        self.assertEqual(original_core, backend.contexts[1]["core"])
        self.assertNotIn("CHANGED DURING WORK", backend.contexts[1]["core"])

        soul.write_text(original + "\nCHANGED", encoding="utf-8")
        resume_backend = SnapshotBackend([decision("blocked")])
        replay = Engine(self.agent, self.workspace, resume_backend).run("", run_dir=self.agent / ".runs" / state["run_id"], feedback="already completed")
        self.assertEqual("completed", replay["status"])

    def test_resume_after_soul_change_uses_saved_snapshot_and_mismatch_has_no_effects(self):
        backend = SnapshotBackend([decision("blocked")])
        state = Engine(self.agent, self.workspace, backend).run("snapshot")
        run_dir = self.agent / ".runs" / state["run_id"]
        before = (run_dir / "state.json").read_bytes()
        old_core = state["core_snapshot"]
        (self.agent / "SOUL.md").write_text("NEW SOUL", encoding="utf-8")
        mismatch = SnapshotBackend([decision("blocked")])
        with self.assertRaises(ContractError):
            Engine(self.agent, self.workspace, mismatch, core_snapshot="wrong").run("", run_dir=run_dir, feedback="retry")
        self.assertEqual(before, (run_dir / "state.json").read_bytes())
        resumed_backend = SnapshotBackend([decision("blocked")])
        resumed = Engine(self.agent, self.workspace, resumed_backend).run("", run_dir=run_dir, feedback="retry")
        self.assertEqual("blocked", resumed["status"])
        self.assertEqual(old_core, resumed_backend.contexts[0]["core"])

    def test_new_run_sees_new_soul_and_legacy_nonterminal_captures_once(self):
        (self.agent / "SOUL.md").write_text("NEW SOUL", encoding="utf-8")
        fresh = SnapshotBackend([decision("blocked")])
        state = Engine(self.agent, self.workspace, fresh).run("new")
        self.assertIn("NEW SOUL", fresh.contexts[0]["core"])
        legacy = json.loads((self.agent / ".runs" / state["run_id"] / "state.json").read_text(encoding="utf-8"))
        legacy.pop("core_snapshot")
        (self.agent / ".runs" / state["run_id"] / "state.json").write_text(json.dumps(legacy), encoding="utf-8")
        (self.agent / "SOUL.md").write_text("LEGACY CURRENT", encoding="utf-8")
        resumed_backend = SnapshotBackend([decision("blocked")])
        resumed = Engine(self.agent, self.workspace, resumed_backend).run("", run_dir=self.agent / ".runs" / state["run_id"], feedback="legacy")
        self.assertIn("LEGACY CURRENT", resumed_backend.contexts[0]["core"])
        self.assertIn("LEGACY CURRENT", resumed["core_snapshot"])

    def test_real_demo_approval_persists_snapshot_across_restart(self):
        before = (self.agent / "SOUL.md").read_text(encoding="utf-8")
        first = Engine(self.agent, self.workspace, DemoBackend(), require_approvals=True).run("demo")
        self.assertEqual("awaiting_approval", first["status"])
        run_dir = self.agent / ".runs" / first["run_id"]
        (self.agent / "SOUL.md").write_text(before + " changed", encoding="utf-8")
        resumed = Engine(self.agent, self.workspace, DemoBackend()).run("", run_dir=run_dir,
            approval_id=first["pending_approval"]["id"], approval_decision="approve")
        self.assertEqual(first["core_snapshot"], resumed["core_snapshot"])
        self.assertEqual("awaiting_approval", resumed["status"])
        final = Engine(self.agent, self.workspace, DemoBackend()).run("", run_dir=run_dir,
            approval_id=resumed["pending_approval"]["id"], approval_decision="approve")
        self.assertEqual("completed", final["status"])
        self.assertTrue(final["reviewed"])
        self.assertEqual(first["core_snapshot"], final["core_snapshot"])
        self.assertIn("ACCEPTED", (self.workspace / "demo-result.md").read_text(encoding="utf-8"))

    def test_invalid_snapshot_inputs_and_persisted_corruption_have_no_effects(self):
        with self.assertRaises(ContractError):
            Engine(self.agent, self.workspace, SnapshotBackend([]), core_snapshot=42)
        with self.assertRaises(ContractError):
            Engine(self.agent, self.workspace, SnapshotBackend([]), core_snapshot="x" * (self.agent.joinpath("agent.json").stat().st_size + 100_000))
        backend = SnapshotBackend([decision("blocked")])
        state = Engine(self.agent, self.workspace, backend).run("bad snapshot")
        path = self.agent / ".runs" / state["run_id"] / "state.json"
        before = path.read_bytes()
        value = json.loads(before)
        value["core_snapshot"] = {"bad": True}
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(ContractError):
            Engine(self.agent, self.workspace, SnapshotBackend([])).run("", run_dir=path.parent, feedback="retry")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["core_snapshot"], {"bad": True})
        value["core_snapshot"] = None
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(ContractError):
            Engine(self.agent, self.workspace, SnapshotBackend([])).run("", run_dir=path.parent, feedback="retry")

    def test_completed_legacy_run_is_idempotent_without_backend_call(self):
        backend = SnapshotBackend([decision(), decision(role="reviewer"), decision("finish")])
        state = Engine(self.agent, self.workspace, backend).run("complete")
        path = self.agent / ".runs" / state["run_id"] / "state.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value.pop("core_snapshot")
        path.write_text(json.dumps(value), encoding="utf-8")
        before = path.read_bytes()
        replay_backend = SnapshotBackend([])
        replay = Engine(self.agent, self.workspace, replay_backend).run("", run_dir=path.parent)
        self.assertEqual("completed", replay["status"])
        self.assertEqual([], replay_backend.contexts)
        self.assertEqual(before, path.read_bytes())


if __name__ == "__main__":
    unittest.main()
