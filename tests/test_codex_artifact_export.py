"""Focused contracts for Codex app-server artifact export and fallback."""

from __future__ import annotations

import base64
import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from agentkit.codex_artifacts import _CHUNK_BYTES, read_codex_artifact
from agentkit.contracts import ContractError
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

    def request(self, request_id, method, params):
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


if __name__ == "__main__":
    unittest.main()
