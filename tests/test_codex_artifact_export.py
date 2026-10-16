"""Focused contracts for Codex app-server artifact export and fallback."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agentkit.codex_artifacts import (
    _CHECK_CODE, _CHUNK_BYTES, _RUNTIME_ROOT, read_codex_artifact, verify_codex_artifact,
)
from agentkit.contracts import ContractError
from agentkit.engine import Engine
from cockpit.server import JobManager


class FakeAppServer:
    responses: list[dict] = []
    instances: list["FakeAppServer"] = []

    def __init__(self, workspace):
        self.workspace = workspace
        self.cwd = workspace.parent
        self.sent: list[dict] = []
        self.requests: list[tuple[int, str, dict]] = []
        self.index = 0
        self.closed = False
        type(self).instances.append(self)

    def send(self, value):
        self.sent.append(value)

    def request(self, request_id, method, params, **kwargs):
        self.requests.append((request_id, method, params))
        response = type(self).responses[self.index]
        self.index += 1
        if isinstance(response, BaseException):
            raise response
        return response

    def close(self):
        self.closed = True


def metadata_response(data: bytes, *, size=None, digest=None, exit_code=0, stdout=True):
    payload = {
        "size": len(data) if size is None else size,
        "sha256": hashlib.sha256(data).hexdigest() if digest is None else digest,
    }
    return {
        "exitCode": exit_code,
        "stdout": json.dumps(payload, separators=(",", ":")) if stdout else stdout,
    }


class CodexArtifactExportTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path.cwd()
        FakeAppServer.instances.clear()

    def call(self, response, relative="result.txt", **kwargs):
        data = kwargs.pop("data", b"")
        chunks = kwargs.pop("chunks", None)
        if chunks is None and response.get("exitCode") == 0:
            chunks = [
                {
                    "exitCode": 0,
                    "stdout": base64.b64encode(data[offset:offset + _CHUNK_BYTES]).decode("ascii"),
                }
                for offset in range(0, len(data), _CHUNK_BYTES)
            ]
        FakeAppServer.responses = [{}, response, *(chunks or [])]
        with patch("agentkit.codex_artifacts._AppServer", FakeAppServer):
            return read_codex_artifact(self.workspace, relative, **kwargs)

    def test_success_uses_readonly_network_false_app_server_and_verifies_payload(self):
        data = "Grüße aus Codex".encode("utf-8")
        self.assertEqual(data, self.call(metadata_response(data), data=data))
        client = FakeAppServer.instances[0]
        self.assertEqual(["initialize", "command/exec", "command/exec"], [item[1] for item in client.requests])
        command = client.requests[1][2]
        self.assertEqual({"type": "readOnly", "networkAccess": False}, command["sandboxPolicy"])
        self.assertEqual(str(self.workspace.parent), command["cwd"])
        self.assertNotIn("outputBytesCap", command)
        self.assertTrue(client.closed)

    def test_success_reassembles_multiple_bounded_chunks(self):
        data = b"x" * (_CHUNK_BYTES + 17)
        self.assertEqual(data, self.call(metadata_response(data), data=data))
        client = FakeAppServer.instances[0]
        self.assertEqual(4, len(client.requests))
        for _, method, params in client.requests[2:]:
            self.assertEqual("command/exec", method)
            self.assertEqual({"type": "readOnly", "networkAccess": False}, params["sandboxPolicy"])

    def test_rejects_bad_base64_hash_size_and_missing_output(self):
        data = b"artifact"
        with self.assertRaises(ContractError):
            self.call(metadata_response(data, digest="0" * 64), data=data)
        with self.assertRaises(ContractError):
            self.call(metadata_response(data, size=len(data) + 1), data=data)
        with self.assertRaises(ContractError):
            self.call(metadata_response(data), data=data,
                      chunks=[{"exitCode": 0, "stdout": "%%%"}])
        with self.assertRaises(ContractError):
            self.call({"exitCode": 0, "stdout": None})

    def test_rejects_path_exit_code_and_size_limits(self):
        data = b"artifact"
        with self.assertRaises(ContractError):
            self.call({"exitCode": 41, "stdout": ""}, relative="../secret.txt")
        with self.assertRaises(ContractError):
            self.call({"exitCode": 43, "stdout": ""})
        with self.assertRaises(ContractError):
            self.call(metadata_response(data), max_bytes=0)
        with self.assertRaises(ContractError):
            self.call(metadata_response(data), max_bytes=2_000_001)

    def test_rejects_nonzero_exit_and_propagates_timeout_as_contract_error(self):
        with self.assertRaises(ContractError):
            self.call({"exitCode": 42, "stdout": ""})
        FakeAppServer.responses = [{}, ContractError("Codex artifact export timed out.")]
        with patch("agentkit.codex_artifacts._AppServer", FakeAppServer), self.assertRaises(ContractError):
            read_codex_artifact(self.workspace, "result.txt")


class SandboxArtifactVerificationTests(unittest.TestCase):
    def test_verification_uses_shared_policy_and_readonly_network_false(self):
        FakeAppServer.instances.clear()
        FakeAppServer.responses = [{}, {"exitCode": 0}]
        with patch("agentkit.codex_artifacts._AppServer", FakeAppServer):
            verify_codex_artifact(Path.cwd(), "proposals/posts.json", timeout=3)
        client = FakeAppServer.instances[0]
        request = client.requests[1][2]
        self.assertEqual({"type": "readOnly", "networkAccess": False}, request["sandboxPolicy"])
        self.assertLessEqual(request["timeoutMs"], 3000)
        self.assertEqual(_RUNTIME_ROOT, request["command"][-1])
        self.assertIn("safe_workspace_path", request["command"][3])
        self.assertTrue(client.closed)

    def test_failed_verification_and_invalid_requests_fail_closed(self):
        FakeAppServer.responses = [{}, {"exitCode": 42}]
        with patch("agentkit.codex_artifacts._AppServer", FakeAppServer):
            with self.assertRaises(ContractError):
                verify_codex_artifact(Path.cwd(), "missing.txt")
        for relative, timeout in (("", 1), (str(Path.cwd()), 1), ("x\0y", 1), ("x", 0)):
            with self.subTest(relative=relative), self.assertRaises(ContractError):
                verify_codex_artifact(Path.cwd(), relative, timeout=timeout)

    def test_real_policy_command_accepts_file_and_rejects_internal_or_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            (workspace / "proposals").mkdir(parents=True)
            (workspace / "proposals/posts.json").write_text("[]", encoding="utf-8")
            (workspace / ".git").mkdir()
            (workspace / ".git/config").write_text("private", encoding="utf-8")
            (workspace.parent / "outside.txt").write_text("outside", encoding="utf-8")
            for relative, accepted in (("proposals/posts.json", True), (".git/config", False),
                                       ("../outside.txt", False), ("missing.txt", False)):
                result = subprocess.run([sys.executable, "-I", "-c", _CHECK_CODE,
                    str(workspace), relative, _RUNTIME_ROOT], capture_output=True, timeout=20)
                with self.subTest(relative=relative):
                    self.assertEqual(accepted, result.returncode == 0)

    def test_engine_only_falls_back_on_codex_permission_errors(self):
        engine = object.__new__(Engine)
        engine.workspace = Path.cwd()
        engine.backend = SimpleNamespace(name="codex")
        for wrapped in (False, True):
            error = PermissionError("sandbox account owns directory")
            if wrapped:
                error = ContractError("Workspace path cannot be inspected safely.")
                error.__cause__ = PermissionError("denied")
            with patch("agentkit.engine.safe_workspace_path", side_effect=error), \
                 patch("agentkit.codex_artifacts.verify_codex_artifact") as verify:
                engine._verify_artifact("proposals/posts.json", 2)
                verify.assert_called_once_with(engine.workspace, "proposals/posts.json", timeout=2)
        for backend, error in (("api", PermissionError("denied")),
                               ("codex", ContractError("internal path"))):
            engine.backend.name = backend
            with patch("agentkit.engine.safe_workspace_path", side_effect=error), \
                 patch("agentkit.codex_artifacts.verify_codex_artifact") as verify:
                with self.assertRaises(type(error)):
                    engine._verify_artifact("proposals/posts.json", 2)
                verify.assert_not_called()


class JobManagerArtifactFallbackTests(unittest.TestCase):
    def setUp(self):
        self.manager = object.__new__(JobManager)
        self.job = type("JobStub", (), {"payload": {"backend": "codex", "workspace": str(Path.cwd())}})()
        self.manager.get = lambda job_id: self.job
        self.manager.snapshot = lambda value: {"result": {"history": [{"report": {"artifacts": ["result.txt"]}}]}}

    def test_codex_permission_error_uses_export_helper(self):
        with patch("cockpit.server.Path.open", side_effect=PermissionError("sandbox-owned file")), \
             patch("cockpit.server.read_codex_artifact", return_value=b"exported") as export:
            self.assertEqual(b"exported", self.manager.artifact("a" * 32, "result.txt"))
            export.assert_called_once_with(Path(self.job.payload["workspace"]), "result.txt")

    def test_non_codex_permission_error_does_not_use_export_helper(self):
        self.job.payload["backend"] = "demo"
        with patch("cockpit.server.Path.open", side_effect=PermissionError("sandbox-owned file")), \
             patch("cockpit.server.read_codex_artifact", return_value=b"must-not-use") as export:
            with self.assertRaises(ContractError):
                self.manager.artifact("a" * 32, "result.txt")
            export.assert_not_called()

    def test_codex_denied_parent_path_uses_same_bounded_export(self):
        error = ContractError("Workspace path cannot be inspected safely.")
        error.__cause__ = PermissionError("sandbox-owned parent")
        with patch("cockpit.server.safe_workspace_path", side_effect=error), \
             patch("cockpit.server.read_codex_artifact", return_value=b"exported") as export:
            self.assertEqual(b"exported", self.manager.artifact("a" * 32, "result.txt"))
            export.assert_called_once_with(Path(self.job.payload["workspace"]), "result.txt")

    def test_unreported_or_unsafe_paths_never_trigger_export(self):
        with patch("cockpit.server.read_codex_artifact") as export:
            with self.assertRaises(ContractError):
                self.manager.artifact("a" * 32, "unreported.txt")
            with patch("cockpit.server.safe_workspace_path", side_effect=ContractError("internal")):
                with self.assertRaises(ContractError):
                    self.manager.artifact("a" * 32, "result.txt")
            export.assert_not_called()


if __name__ == "__main__":
    unittest.main()
