"""SubagentManager — spec parsing, selection, and execution. ``run`` calls the
model via ``brain.complete``, which is mocked here (WP-C1 backfill)."""

from pathlib import Path

import brain

from core.context import ProjectContext, SkillSpec
from core.subagents import SubagentManager, SubagentSpec


RESEARCHER_MD = """---
name: researcher
description: Investigates topics
keywords: [research, analyse, investigate]
can_write: false
---
You are a researcher. Gather facts.
"""

REPORTER_MD = """---
name: reporter
description: Writes reports
keywords: [report, summarize]
can_write: true
---
You are a reporter. Produce the final write-up.
"""


def _ctx(**kw) -> ProjectContext:
    return ProjectContext(project_root=Path("."), **kw)


def _mgr() -> SubagentManager:
    return SubagentManager(Path("."))


def _both_agents_ctx() -> ProjectContext:
    return _ctx(subagents={"researcher": RESEARCHER_MD, "reporter": REPORTER_MD})


def test_load_parses_frontmatter_specs():
    specs = _mgr().load(_both_agents_ctx())
    assert set(specs) == {"researcher", "reporter"}
    assert specs["researcher"].can_write is False
    assert "research" in specs["researcher"].keywords
    assert specs["reporter"].can_write is True


def test_select_by_keyword_scoring():
    spec = _mgr().select("please research the competitors", context=_both_agents_ctx())
    assert spec is not None
    assert spec.name == "researcher"


def test_select_falls_back_to_researcher_when_no_match():
    spec = _mgr().select("xyzzy", context=_both_agents_ctx())
    assert spec is not None
    assert spec.name == "researcher"


def test_select_returns_none_without_specs():
    assert _mgr().select("anything", context=_ctx()) is None


def test_select_by_skill_expected_subagent():
    skill = SkillSpec(
        name="deep-dive",
        triggers=["deep dive"],
        body="Use a subagent.\nexpected_subagent: reporter",
    )
    ctx = _ctx(subagents={"researcher": RESEARCHER_MD, "reporter": REPORTER_MD}, skills={"deep-dive": skill})
    spec = _mgr().select("please deep dive on this", context=ctx)
    assert spec.name == "reporter"


def test_leaf_writer_picks_the_declared_writer():
    writer = _mgr().leaf_writer(_both_agents_ctx())
    assert writer is not None
    assert writer.name == "reporter"


def test_leaf_writer_none_when_no_writer():
    ctx = _ctx(subagents={"researcher": RESEARCHER_MD})
    assert _mgr().leaf_writer(ctx) is None


def test_run_uses_model_output(monkeypatch):
    monkeypatch.setattr(brain, "complete", lambda *a, **k: "  the researched answer  ")
    spec = SubagentSpec(name="researcher", keywords=["research"])
    result = _mgr().run(spec, task="research X", context=_ctx())
    assert result["subagent"] == "researcher"
    assert result["output"] == "the researched answer"
    assert result["can_write"] is False


def test_run_falls_back_when_model_empty(monkeypatch):
    monkeypatch.setattr(brain, "complete", lambda *a, **k: "")
    spec = SubagentSpec(name="researcher", keywords=["research", "study"])
    result = _mgr().run(spec, task="research X", context=_ctx())
    assert "Fallback summary" in result["output"]
    assert "research" in result["output"]


def test_run_includes_active_skill_context(monkeypatch):
    captured = {}

    def _fake_complete(system, user, **kw):
        captured["system"] = system
        return "ok"

    monkeypatch.setattr(brain, "complete", _fake_complete)
    skill = SkillSpec(name="pricing", triggers=["price"], body="Pricing rules body",
                      references={"examples": "example ref text"})
    ctx = _ctx(skills={"pricing": skill})
    _mgr().run(SubagentSpec(name="researcher"), task="what is the price", context=ctx)
    assert "Active Skill: pricing" in captured["system"]
    assert "example ref text" in captured["system"]


def test_default_subagent_model_from_manifest():
    mgr = _mgr()
    ctx = _ctx(manifest={"model": {"subagents": "claude-sonnet-5"}})
    assert mgr._default_subagent_model(ctx) == "claude-sonnet-5"
    assert mgr._default_subagent_model(None) == "claude-haiku-4-5"


def test_default_keywords_for_known_role():
    spec = _mgr()._parse_spec("verifier", "---\nname: verifier\n---\nbody")
    assert "verify" in spec.keywords
