"""Tests für handoff.py — HandoffRouter, HandoffRequest, Validierung."""
import pytest
from core.handoff import HandoffRequest, HandoffRouter, load_router


ALLOWLIST = ["reader", "compute", "writer"]


@pytest.fixture
def router() -> HandoffRouter:
    return HandoffRouter(allowlist=ALLOWLIST, max_payload_chars=2000)


class TestHandoffRequest:
    def test_payload_size_empty_context(self):
        req = HandoffRequest(target="reader", task="Analysiere Daten")
        size = req.payload_size()
        assert size == len("Analysiere Daten") + len("{}")

    def test_payload_size_with_context(self):
        ctx = {"key": "value"}
        req = HandoffRequest(target="reader", task="Task", context=ctx)
        assert req.payload_size() > len("Task")


class TestHandoffRouterExtract:
    def test_extract_valid_block(self, router):
        text = """Ich werde den Reader beauftragen.
<<HANDOFF>>
{"target": "reader", "task": "Analysiere report.csv", "context": {"focus": "umsatz"}}
<<END_HANDOFF>>
Fertig."""
        req = router.extract(text)
        assert req is not None
        assert req.target == "reader"
        assert req.task == "Analysiere report.csv"
        assert req.context == {"focus": "umsatz"}

    def test_extract_no_block_returns_none(self, router):
        assert router.extract("Normaler Text ohne Handoff") is None

    def test_extract_invalid_json_returns_none(self, router):
        text = "<<HANDOFF>>{nicht valid json}<<END_HANDOFF>>"
        assert router.extract(text) is None

    def test_extract_missing_target_returns_none(self, router):
        text = '<<HANDOFF>>{"task": "Aufgabe"}<<END_HANDOFF>>'
        assert router.extract(text) is None

    def test_extract_missing_task_returns_none(self, router):
        text = '<<HANDOFF>>{"target": "reader"}<<END_HANDOFF>>'
        assert router.extract(text) is None

    def test_extract_case_insensitive(self, router):
        text = '<<handoff>>{"target": "reader", "task": "Task"}<<END_HANDOFF>>'
        req = router.extract(text)
        assert req is not None

    def test_extract_empty_context_defaults_to_dict(self, router):
        text = '<<HANDOFF>>{"target": "reader", "task": "Task"}<<END_HANDOFF>>'
        req = router.extract(text)
        assert req is not None
        assert req.context == {}

    def test_extract_first_block_wins(self, router):
        text = (
            '<<HANDOFF>>{"target": "reader", "task": "Erste"}<<END_HANDOFF>>'
            '<<HANDOFF>>{"target": "writer", "task": "Zweite"}<<END_HANDOFF>>'
        )
        req = router.extract(text)
        assert req.target == "reader"


class TestHandoffRouterExtractFromPlan:
    def test_extract_from_plan_present(self, router):
        plan = {"tool": None, "handoff": {"target": "reader", "task": "Aufgabe"}}
        req = router.extract_from_plan(plan)
        assert req is not None
        assert req.target == "reader"

    def test_extract_from_plan_absent_returns_none(self, router):
        plan = {"tool": "file", "tool_input": "read:test.txt"}
        assert router.extract_from_plan(plan) is None

    def test_extract_from_plan_none_value_returns_none(self, router):
        plan = {"handoff": None}
        assert router.extract_from_plan(plan) is None


class TestHandoffRouterValidate:
    def test_valid_request_passes(self, router):
        req = HandoffRequest(target="reader", task="Aufgabe")
        ok, reason = router.validate(req)
        assert ok is True
        assert reason == ""

    def test_target_not_in_allowlist(self, router):
        req = HandoffRequest(target="hacker", task="Böse Aufgabe")
        ok, reason = router.validate(req)
        assert ok is False
        assert "hacker" in reason
        assert "Allowlist" in reason

    def test_payload_too_large(self, router):
        req = HandoffRequest(target="reader", task="x" * 3000)
        ok, reason = router.validate(req)
        assert ok is False
        assert "groß" in reason.lower() or "Maximum" in reason

    def test_max_payload_exactly_at_limit_passes(self):
        router = HandoffRouter(allowlist=["reader"], max_payload_chars=100)
        req = HandoffRequest(target="reader", task="x" * 95)
        ok, _ = router.validate(req)
        assert ok is True

    def test_max_payload_one_over_fails(self):
        router = HandoffRouter(allowlist=["reader"], max_payload_chars=10)
        req = HandoffRequest(target="reader", task="x" * 20)
        ok, _ = router.validate(req)
        assert ok is False

    def test_all_allowlist_targets_pass(self, router):
        for target in ALLOWLIST:
            req = HandoffRequest(target=target, task="Aufgabe")
            ok, _ = router.validate(req)
            assert ok is True, f"{target} sollte erlaubt sein"


class TestHandoffRouterAllowlist:
    def test_allowlist_property_sorted(self):
        router = HandoffRouter(allowlist=["writer", "reader", "compute"])
        assert router.allowlist == ["compute", "reader", "writer"]

    def test_empty_allowlist(self):
        router = HandoffRouter(allowlist=[])
        req = HandoffRequest(target="reader", task="Task")
        ok, _ = router.validate(req)
        assert ok is False


class TestLoadRouter:
    def test_load_with_none_returns_empty_allowlist(self):
        router = load_router(None)
        assert router.allowlist == []

    def test_load_with_manifest(self, manifest):
        router = load_router(manifest)
        assert "reader" in router.allowlist
        assert "writer" in router.allowlist

    def test_load_respects_max_payload(self):
        manifest = {"handoffs": {"allowlist": ["reader"], "max_payload_chars": 500}}
        router = load_router(manifest)
        req = HandoffRequest(target="reader", task="x" * 600)
        ok, _ = router.validate(req)
        assert ok is False
