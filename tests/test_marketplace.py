"""Invarianten der Agenten-Mietplattform (prototype/data.js + app.js)."""
from pathlib import Path
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parent.parent


def _node(script: str) -> str:
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


def test_js_syntax():
        for rel in ("prototype/app.js", "prototype/data.js", "prototype/product-client.js"):
        r = subprocess.run(["node", "--check", str(ROOT / rel)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_catalog_invariants():
    script = textwrap.dedent(
        r"""
        const fs = require("fs");
        const vm = require("vm");
        const ctx = { window: {} };
        vm.createContext(ctx);
        const exported = vm.runInContext(
          fs.readFileSync("prototype/data.js", "utf8") +
          "\n({ AGENT_CATALOG, MODULES, SCENARIOS, MODULE_GROUPS, AGENT_CATEGORIES })",
          ctx
        );
        const cat = exported.AGENT_CATALOG;
        const MODULES = exported.MODULES;
        const SCENARIOS = exported.SCENARIOS;
        if (!Array.isArray(cat) || cat.length < 8) throw new Error("catalog too small: " + (cat && cat.length));
        const ids = cat.map((a) => a.id);
        if (new Set(ids).size !== ids.length) throw new Error("duplicate ids");
        const required = ["auskunft", "reporting", "rechnung", "vertrag"];
        for (const id of required) if (!ids.includes(id)) throw new Error("missing " + id);
        const auskunft = cat.find((a) => a.id === "auskunft");
        if (!auskunft.included || auskunft.price !== 0) throw new Error("auskunft must be included/0");
        const rec = cat.find((a) => a.recommended);
        if (!rec || rec.id !== "reporting" || rec.price !== 400) throw new Error("reporting must be recommended @400");
        for (const a of cat) {
          if (!a.name || !a.role || !a.desc || !a.category) throw new Error("incomplete " + a.id);
          if (!Array.isArray(a.skills) || a.skills.length < 2) throw new Error("skills " + a.id);
          if (!Array.isArray(a.tasks) || !a.tasks.length) throw new Error("tasks " + a.id);
          if (!a.included && !(a.price >= 400)) throw new Error("price floor " + a.id);
        }
        const modules = MODULES.map((m) => m.key);
        if (!modules.includes("team")) throw new Error("no team module");
        const money = SCENARIOS.find((s) => s.id === "agent-dazubuchen");
        if (!money || !money.answer.agents || money.answer.agents.length !== 4)
          throw new Error("money-shot agents");
        for (const a of money.answer.agents) {
          if (!ids.includes(a.id)) throw new Error("money-shot id not in catalog: " + a.id);
        }
        if (cat.length !== 8) throw new Error("expected 8 agents, got " + cat.length);
        console.log("ok " + ids.join(","));
        """
    )
    out = _node(script)
    assert out.startswith("ok ")
    assert "auskunft" in out and "reporting" in out


def test_answer_card_defined():
    src = (ROOT / "prototype" / "app.js").read_text(encoding="utf-8")
    assert "function answerCard(" in src
    assert "function renderTeamView(" in src
    assert "function rentAgent(" in src
    assert "function openRent(" in src


def test_money_shot_finale_untouched():
    src = (ROOT / "prototype" / "app.js").read_text(encoding="utf-8")
    assert 'const MONEY_SHOT_ID = "agent-dazubuchen"' in src
    assert "MONEY_SHOT_ID" in src
    assert "DEMO_ORDER" in src
