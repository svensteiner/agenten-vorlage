"""Tests for tools/check.py — the project-pack validator."""
import importlib.util
import sys
from pathlib import Path

# Load tools/check.py as a module (it lives outside a package). It must be
# registered in sys.modules before exec so dataclasses can resolve its module.
_CHECK_PATH = Path(__file__).resolve().parent.parent / "tools" / "check.py"
_spec = importlib.util.spec_from_file_location("check", _CHECK_PATH)
check = importlib.util.module_from_spec(_spec)
sys.modules["check"] = check
_spec.loader.exec_module(check)


class TestCheckResult:
    def test_ok_when_no_errors(self):
        r = check.CheckResult()
        r.warn("nur warnung")
        assert r.ok is True

    def test_not_ok_with_error(self):
        r = check.CheckResult()
        r.error("kaputt")
        assert r.ok is False

    def test_to_dict_shape(self):
        r = check.CheckResult()
        r.error("e")
        r.warn("w")
        r.info("i")
        d = r.to_dict()
        assert d["ok"] is False
        assert d["errors"] == ["e"] and d["warnings"] == ["w"] and d["infos"] == ["i"]


class TestManifestChecks:
    def _run(self, tmp_path: Path, manifest: dict, monkeypatch) -> check.CheckResult:
        import json

        project = tmp_path / "project"
        project.mkdir()
        (project / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (tmp_path / "config.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(check, "ROOT", tmp_path)
        monkeypatch.setattr(check, "PROJECT", project)
        return check.run_checks()

    def test_valid_leaf_write_passes(self, tmp_path, monkeypatch):
        manifest = {
            "autonomy_level": "gated",
            "workers": {
                "reader": {"tools": ["file_read"], "trust_level": "low"},
                "writer": {"tools": ["file_write"], "trust_level": "high"},
            },
            "handoffs": {"allowlist": ["reader", "writer"]},
        }
        r = self._run(tmp_path, manifest, monkeypatch)
        assert r.ok is True

    def test_two_writers_fails_leaf_write(self, tmp_path, monkeypatch):
        manifest = {
            "workers": {
                "w1": {"tools": ["file_write"], "trust_level": "high"},
                "w2": {"tools": ["file_write"], "trust_level": "high"},
            }
        }
        r = self._run(tmp_path, manifest, monkeypatch)
        assert r.ok is False
        assert any("Leaf-Write" in e for e in r.errors)

    def test_invalid_trust_level_fails(self, tmp_path, monkeypatch):
        manifest = {"workers": {"x": {"tools": [], "trust_level": "godmode"}}}
        r = self._run(tmp_path, manifest, monkeypatch)
        assert r.ok is False

    def test_handoff_to_unknown_worker_fails(self, tmp_path, monkeypatch):
        manifest = {
            "workers": {"reader": {"tools": ["file_read"], "trust_level": "low"}},
            "handoffs": {"allowlist": ["ghost"]},
        }
        r = self._run(tmp_path, manifest, monkeypatch)
        assert r.ok is False
        assert any("ghost" in e for e in r.errors)

    def test_max_autonomy_warns(self, tmp_path, monkeypatch):
        r = self._run(tmp_path, {"autonomy_level": "max"}, monkeypatch)
        assert r.ok is True
        assert any("max" in w for w in r.warnings)

    def test_missing_manifest_errors(self, tmp_path, monkeypatch):
        monkeypatch.setattr(check, "ROOT", tmp_path)
        monkeypatch.setattr(check, "PROJECT", tmp_path / "project")
        r = check.run_checks()
        assert r.ok is False


class TestExitCode:
    def test_main_returns_zero_on_clean(self, tmp_path, monkeypatch):
        import json

        project = tmp_path / "project"
        project.mkdir()
        (project / "manifest.json").write_text(
            json.dumps({"autonomy_level": "gated"}), encoding="utf-8"
        )
        (tmp_path / "config.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(check, "ROOT", tmp_path)
        monkeypatch.setattr(check, "PROJECT", project)
        assert check.main([]) == 0

    def test_main_strict_fails_on_warning(self, tmp_path, monkeypatch):
        import json

        project = tmp_path / "project"
        project.mkdir()
        (project / "manifest.json").write_text(
            json.dumps({"autonomy_level": "max"}), encoding="utf-8"
        )
        (tmp_path / "config.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(check, "ROOT", tmp_path)
        monkeypatch.setattr(check, "PROJECT", project)
        assert check.main(["--strict"]) == 1
