"""Tests für workers.py — WorkerRegistry und Least-Privilege."""
import pytest
from core.workers import Worker, WorkerRegistry, _ScopedFileTool, load_registry


class TestWorker:
    def test_can_use_direct_match(self):
        w = Worker("reader", "", ("file_read", "web_search"), "low")
        assert w.can_use("file_read") is True
        assert w.can_use("web_search") is True

    def test_can_use_alias(self):
        w = Worker("reader", "", ("file_read",), "low")
        assert w.can_use("file") is True  # file_read → file alias

    def test_cannot_use_unlisted(self):
        w = Worker("reader", "", ("file_read",), "low")
        assert w.can_use("notify") is False
        assert w.can_use("file_write") is False

    def test_frozen_dataclass(self):
        w = Worker("reader", "", ("file_read",), "low")
        with pytest.raises((AttributeError, TypeError)):
            w.name = "hacker"  # type: ignore


class TestWorkerRegistry:
    def test_loads_workers_from_manifest(self, manifest):
        reg = WorkerRegistry(manifest)
        assert "reader" in reg.names()
        assert "compute" in reg.names()
        assert "writer" in reg.names()

    def test_empty_manifest_gives_empty_registry(self):
        reg = WorkerRegistry({})
        assert reg.names() == []

    def test_get_known_worker(self, manifest):
        reg = WorkerRegistry(manifest)
        w = reg.get("reader")
        assert w is not None
        assert w.trust_level == "low"

    def test_get_unknown_worker_returns_none(self, manifest):
        reg = WorkerRegistry(manifest)
        assert reg.get("nonexistent") is None

    def test_check_permission_allowed(self, manifest):
        reg = WorkerRegistry(manifest)
        ok, reason = reg.check_permission("reader", "web_search")
        assert ok is True
        assert reason == ""

    def test_check_permission_denied(self, manifest):
        reg = WorkerRegistry(manifest)
        ok, reason = reg.check_permission("reader", "notify")
        assert ok is False
        assert "reader" in reason
        assert "notify" in reason

    def test_check_permission_unknown_worker_allows_all(self, manifest):
        reg = WorkerRegistry(manifest)
        ok, _ = reg.check_permission("nonexistent_worker", "any_tool")
        assert ok is True

    def test_filter_tools_reader(self, manifest, mock_tool):
        reg = WorkerRegistry(manifest)
        all_tools = {
            "web_search": mock_tool,
            "notify": mock_tool,
            "file": mock_tool,
        }
        filtered = reg.filter_tools("reader", all_tools)
        assert "web_search" in filtered
        assert "notify" not in filtered

    def test_filter_tools_writer(self, manifest, mock_tool):
        reg = WorkerRegistry(manifest)
        all_tools = {
            "web_search": mock_tool,
            "notify": mock_tool,
            "file": mock_tool,
        }
        filtered = reg.filter_tools("writer", all_tools)
        assert "notify" in filtered
        assert "web_search" not in filtered

    def test_filter_tools_compute_gets_nothing(self, manifest, mock_tool):
        reg = WorkerRegistry(manifest)
        all_tools = {"web_search": mock_tool, "notify": mock_tool, "file": mock_tool}
        filtered = reg.filter_tools("compute", all_tools)
        assert filtered == {}

    def test_filter_tools_unknown_worker_gets_all(self, manifest, mock_tool):
        reg = WorkerRegistry(manifest)
        all_tools = {"web_search": mock_tool, "notify": mock_tool}
        filtered = reg.filter_tools("unknown", all_tools)
        assert filtered == all_tools

    def test_summary_structure(self, manifest):
        reg = WorkerRegistry(manifest)
        s = reg.summary()
        assert "reader" in s
        assert "tools" in s["reader"]
        assert "trust" in s["reader"]

    def test_write_workers_count(self, manifest):
        reg = WorkerRegistry(manifest)
        write_workers = [
            name for name in reg.names()
            if reg.get(name) and reg.get(name).can_use("file_write")
        ]
        assert len(write_workers) == 1
        assert write_workers[0] == "writer"


class TestScopedFileTool:
    def _make_original(self):
        class FakeTool:
            name = "file"
            def safe_run(self, inp: str) -> str:
                return f"OK:{inp}"
        return FakeTool()

    def test_read_only_worker_can_read(self):
        orig = self._make_original()
        scoped = _ScopedFileTool(orig, ("file_read",))
        result = scoped.safe_run("read:test.txt")
        assert result == "OK:read:test.txt"

    def test_read_only_worker_cannot_write(self):
        orig = self._make_original()
        scoped = _ScopedFileTool(orig, ("file_read",))
        result = scoped.safe_run("write:test.txt|content")
        assert "FEHLER" in result

    def test_write_only_worker_can_write(self):
        orig = self._make_original()
        scoped = _ScopedFileTool(orig, ("file_write",))
        result = scoped.safe_run("write:test.txt|content")
        assert result == "OK:write:test.txt|content"

    def test_write_only_worker_cannot_read(self):
        orig = self._make_original()
        scoped = _ScopedFileTool(orig, ("file_write",))
        result = scoped.safe_run("read:test.txt")
        assert "FEHLER" in result


class TestLoadRegistry:
    def test_load_with_none_returns_empty(self):
        reg = load_registry(None)
        assert reg.names() == []

    def test_load_with_manifest(self, manifest):
        reg = load_registry(manifest)
        assert len(reg.names()) == 3
