import tempfile
import unittest
from pathlib import Path

from agentkit.backends import DemoBackend
from agentkit.contracts import ContractError
from agentkit.engine import Engine
from agentkit.routing import EscalatingBackend
from agentkit.scaffold import create


class Stub:
    name = "stub"
    supports_action_approvals = True

    def __init__(self, model):
        self.model = model
        self.calls = []

    def decide(self, context, timeout):
        self.calls.append(("plan", timeout))
        return {"action": "blocked"}

    def execute(self, decision, context, timeout):
        self.calls.append(("work", timeout))
        return {"status": "success"}


def entry(status, role="developer", evidence=None):
    return {"decision": {"role": role}, "report": {"status": status, "evidence": evidence or []}}


def context(*history):
    return {"history": list(history), "catalog": {"roles": {
        "developer": {"can_review": False}, "reviewer": {"can_review": True}}}}


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.cheap, self.strong, self.review = (Stub(name) for name in ("cheap", "strong", "review"))
        self.backend = EscalatingBackend(self.cheap, recovery=self.strong, reviewer=self.review)

    def execute(self, ctx, role="developer"):
        return self.backend.execute({"role": role}, ctx, 17)

    def test_planner_stays_primary_and_first_worker_is_primary(self):
        self.backend.decide(context(entry("needs_revision"), entry("needs_revision")), 11)
        self.execute(context())
        self.assertEqual([("plan", 11), ("work", 17)], self.cheap.calls)
        self.assertEqual([], self.strong.calls)

    def test_two_revisions_escalate_even_when_developer_claimed_success(self):
        ctx = context(entry("needs_revision", "reviewer"), entry("success"),
                      entry("needs_revision", "reviewer"))
        self.execute(ctx)
        self.assertEqual([("work", 17)], self.strong.calls)
        self.assertEqual("strong", self.backend.execution_route({"role": "developer"}, ctx)["model"])

    def test_successful_review_resets_episode_only_with_evidence(self):
        failures = [entry("needs_revision"), entry("needs_revision")]
        self.execute(context(*failures, entry("success", "reviewer")))
        self.execute(context(*failures, entry("success", "reviewer", ["fresh review"])))
        self.assertEqual(1, len(self.strong.calls))
        self.assertEqual(1, len(self.cheap.calls))

    def test_blocked_reports_do_not_trigger_model_retry(self):
        self.execute(context(entry("blocked"), entry("blocked")))
        self.assertEqual(1, len(self.cheap.calls))
        self.assertEqual([], self.strong.calls)

    def test_review_route_uses_capability_not_role_name(self):
        ctx = context()
        ctx["catalog"]["roles"]["independent-auditor"] = {"can_review": True}
        self.execute(ctx, "independent-auditor")
        self.assertEqual([("work", 17)], self.review.calls)

    def test_exception_propagates_without_an_automatic_retry(self):
        def fail(*args):
            raise TimeoutError("unknown outcome")
        self.cheap.execute = fail
        with self.assertRaises(TimeoutError):
            self.execute(context())
        self.assertEqual([], self.strong.calls)

    def test_invalid_threshold_and_mixed_provider_are_rejected(self):
        for value in (0, True, 11):
            with self.subTest(value=value), self.assertRaises(ContractError):
                EscalatingBackend(self.cheap, recovery=self.strong, repair_after=value)
        self.strong.name = "different-provider"
        with self.assertRaises(ContractError):
            EscalatingBackend(self.cheap, recovery=self.strong)

    def test_changed_configured_model_changes_approval_identity(self):
        before = self.backend.approval_identity
        self.strong.model = "replacement"
        self.assertNotEqual(before, self.backend.approval_identity)

    def test_engine_repairs_after_two_failures_then_reviews_without_resetting_budget(self):
        def report(status, artifacts=()):
            return {"status": status, "summary": "bounded fixture", "artifacts": list(artifacts),
                    "evidence": ["fresh fixture evidence"], "next_actions": []}
        def decide(ctx, timeout):
            reports = [row["report"] for row in ctx["history"] if "report" in row]
            if ctx["review_pending"] and reports and reports[-1]["status"] == "success":
                role = "reviewer"
            elif reports and ctx["review_pending"] is False:
                return {"action": "finish", "role": "", "skills": [],
                        "task": "Artifact fixed and independently reviewed", "reason": "verified"}
            else:
                role = "developer"
            return {"action": "delegate", "role": role, "skills": [],
                    "task": "Fix and verify the fixture artifact", "reason": "remaining work"}
        def repair(decision, ctx, timeout):
            (Path(ctx["workspace"]) / "result.txt").write_text("fixed", encoding="utf-8")
            return report("success", ["result.txt"])
        def review(decision, ctx, timeout):
            self.assertEqual("fixed", (Path(ctx["workspace"]) / "result.txt").read_text())
            return report("success", ["result.txt"])
        self.cheap.decide = decide
        self.cheap.execute = lambda *args: report("needs_revision")
        self.strong.execute = repair
        self.review.execute = review
        with tempfile.TemporaryDirectory() as temp:
            pack = create(Path(temp) / "agent", "developer", "agent", "company")
            state = Engine(pack, pack / "workspace", self.backend).run("repair fixture")
            self.assertEqual("completed", state["status"])
            self.assertTrue(state["reviewed"])
            self.assertEqual(2, state["failures"])
            self.assertEqual(5, state["steps"])
            self.assertEqual(["cheap", "cheap", "strong", "review"],
                [row["model_route"]["model"] for row in state["history"] if "model_route" in row])

    def test_approval_binds_full_policy_and_unchanged_policy_can_resume(self):
        def routed(recovery="strong"):
            primary, repair = DemoBackend(), DemoBackend()
            primary.model, repair.model = "cheap", recovery
            return EscalatingBackend(primary, recovery=repair)
        with tempfile.TemporaryDirectory() as temp:
            pack = create(Path(temp) / "agent", "developer", "agent", "company")
            workspace = pack / "workspace"
            state = Engine(pack, workspace, routed(), require_approvals=True).run("demo")
            run_dir = pack / ".runs" / state["run_id"]
            with self.assertRaisesRegex(ContractError, "stale|bound"):
                Engine(pack, workspace, routed("changed")).run("", run_dir=run_dir,
                    approval_id=state["pending_approval"]["id"], approval_decision="approve")
            for _ in range(2):
                state = Engine(pack, workspace, routed()).run("", run_dir=run_dir,
                    approval_id=state["pending_approval"]["id"], approval_decision="approve")
            self.assertEqual("completed", state["status"])
            self.assertTrue(state["reviewed"])
            self.assertEqual("cheap", state["history"][0]["model_route"]["model"])
