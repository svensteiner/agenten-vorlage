import tempfile
import unittest
from pathlib import Path

from agentkit.backends import DeepSeekBackend, DemoBackend
from agentkit.contracts import ContractError
from agentkit.engine import Engine
from agentkit.routing import EscalatingBackend
from agentkit.scaffold import create
from agentkit.write_policy import WritePolicy


class Stub:
    name = "stub"
    supports_action_approvals = True
    supports_write_policy = True

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

    def test_routing_rejects_same_backend_name_with_different_endpoints(self):
        primary = DeepSeekBackend(model="cheap", api_key="test", base_url="https://api.deepseek.com")
        recovery = DeepSeekBackend(
            model="strong", api_key="test", base_url="https://provider.example/v1"
        )
        with self.assertRaisesRegex(ContractError, "provider endpoint"):
            EscalatingBackend(primary, recovery=recovery)

    def test_claimed_identity_cannot_hide_different_transport_urls(self):
        primary = DeepSeekBackend(model="cheap", api_key="test", base_url="https://api.deepseek.com")
        recovery = DeepSeekBackend(
            model="strong", api_key="test", base_url="https://provider.example/v1"
        )
        primary.endpoint_identity = recovery.endpoint_identity = "https://api.deepseek.com"
        with self.assertRaisesRegex(ContractError, "does not match the transport"):
            EscalatingBackend(primary, recovery=recovery)

    def test_matching_normalized_endpoint_routes_models_and_binds_identity(self):
        primary = DeepSeekBackend(
            model="cheap", api_key="test", base_url="https://API.DeepSeek.com/"
        )
        recovery = DeepSeekBackend(
            model="strong", api_key="test", base_url="https://api.deepseek.com"
        )
        primary.endpoint_identity = recovery.endpoint_identity = "https://api.deepseek.com"
        routed = EscalatingBackend(primary, recovery=recovery)
        before = routed.approval_identity
        self.assertEqual("https://api.deepseek.com", routed._endpoint_identities[0])
        self.assertEqual("cheap", routed.execution_route({"role": "developer"}, context())["model"])
        recovery.base_url = "https://other.example"
        with self.assertRaisesRegex(ContractError, "does not match the transport"):
            _ = routed.approval_identity
        with self.assertRaisesRegex(ContractError, "does not match the transport"):
            routed.execute({"role": "developer"}, context(), 1)
        self.assertNotEqual(before, "")

    def test_write_policy_capability_requires_every_routed_backend(self):
        self.assertTrue(self.backend.supports_write_policy)
        self.review.supports_write_policy = False
        with_reviewer = EscalatingBackend(
            self.cheap, recovery=self.strong, reviewer=self.review
        )
        self.assertFalse(with_reviewer.supports_write_policy)
        without_reviewer = EscalatingBackend(self.cheap, recovery=self.strong)
        self.assertTrue(without_reviewer.supports_write_policy)
        self.strong.supports_write_policy = False
        with_recovery = EscalatingBackend(self.cheap, recovery=self.strong)
        self.assertFalse(with_recovery.supports_write_policy)

    def test_routed_backend_preserves_context_identity_for_selected_worker(self):
        ctx = context(entry("needs_revision"), entry("needs_revision"))
        observed = []
        self.strong.execute = lambda decision, received, timeout: observed.append(
            (received, received["write_policy"], received["request_approval"])
        ) or {"status": "success"}
        sentinel_policy = object()
        def sentinel_callback(*args):
            return None
        ctx.update(write_policy=sentinel_policy, request_approval=sentinel_callback)
        self.execute(ctx)
        self.assertIs(ctx, observed[0][0])
        self.assertIs(sentinel_policy, observed[0][1])
        self.assertIs(sentinel_callback, observed[0][2])

    def test_engine_rejects_routed_policy_if_any_backend_lacks_capability(self):
        self.review.supports_write_policy = False
        unsafe_backend = EscalatingBackend(
            self.cheap, recovery=self.strong, reviewer=self.review
        )
        with tempfile.TemporaryDirectory() as temp:
            agent = create(Path(temp) / "agent", "developer", "agent", "company")
            with self.assertRaisesRegex(ContractError, "strict write policy"):
                Engine(
                    agent, agent / "workspace", unsafe_backend,
                    write_policy=WritePolicy(["allowed.txt"]),
                )

    def test_planner_gets_json_safe_policy_summary(self):
        policy = WritePolicy(["content/post.md"])
        seen = []
        self.cheap.decide = lambda ctx, timeout: seen.append(ctx) or {
            "action": "blocked", "role": "", "skills": [],
            "task": "No work", "reason": "fixture",
        }
        with tempfile.TemporaryDirectory() as temp:
            agent = create(Path(temp) / "agent", "developer", "agent", "company")
            Engine(agent, agent / "workspace", self.backend, write_policy=policy).run("fixture")
        summary = seen[0]["write_policy_summary"]
        self.assertEqual(policy.sha256, summary["sha256"])
        self.assertEqual(["content/post.md"], summary["allowed_files"])
        self.assertNotIn("write_policy", seen[0])

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

    def test_endpoint_change_blocks_pending_approval_resume(self):
        def routed():
            primary, repair = DemoBackend(), DemoBackend()
            primary.model, repair.model = "cheap", "strong"
            primary.base_url = repair.base_url = "https://provider.example/v1"
            primary.endpoint_identity = repair.endpoint_identity = "https://provider.example/v1"
            return EscalatingBackend(primary, recovery=repair), primary, repair

        with tempfile.TemporaryDirectory() as temp:
            pack = create(Path(temp) / "agent", "developer", "agent", "company")
            workspace = pack / "workspace"
            backend, primary, repair = routed()
            state = Engine(pack, workspace, backend, require_approvals=True).run("demo")
            run_dir = pack / ".runs" / state["run_id"]
            primary.base_url = repair.base_url = "https://other.example/v1"
            with self.assertRaisesRegex(ContractError, "does not match the transport"):
                Engine(pack, workspace, backend, require_approvals=True).run(
                    "", run_dir=run_dir,
                    approval_id=state["pending_approval"]["id"],
                    approval_decision="approve",
                )
            self.assertFalse((workspace / "demo-result.md").exists())
