"""Read Codex-owned Windows artifacts through the same read-only sandbox.

The elevated Windows sandbox can leave newly created files owned by its dedicated
account.  The host must not change their ACLs or run an unsandboxed helper.  This
module asks the official Codex app-server to read one already reported artifact
under a read-only, network-disabled policy and returns a bounded, hash-checked
payload to the host.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, TextIO

from .backends import (
    _windows_sandbox_selection,
    codex_command,
    subprocess_environment,
)
from .contracts import ContractError

MAX_ARTIFACT_BYTES = 2_000_000
_CHUNK_BYTES = 262_144
_COMMAND_TIMEOUT_MS = 15_000
_RESPONSE_TIMEOUT_SECONDS = 20.0
_RUNTIME_ROOT = str(Path(__file__).resolve().parents[1])
_SAFE_TARGET_CODE = (
    "import pathlib,sys;"
    "sys.dont_write_bytecode=True;"
    "sys.path.insert(0,sys.argv[-1]);"
    "from agentkit.approvals import safe_workspace_path;"
    "root=pathlib.Path(sys.argv[1]).resolve(strict=True);"
    "target=safe_workspace_path(root,sys.argv[2]);"
    "target.is_file() or sys.exit(42);"
)
_CHECK_CODE = _SAFE_TARGET_CODE
_METADATA_CODE = (
    _SAFE_TARGET_CODE
    + "import base64,hashlib,json;"
    "limit=int(sys.argv[3]);"
    "target.stat().st_size<=limit or sys.exit(43);"
    "data=target.read_bytes();"
    "len(data)<=limit or sys.exit(43);"
    "sys.stdout.write(json.dumps({'size':len(data),'sha256':hashlib.sha256(data).hexdigest()},"
    "separators=(',',':')))"
)
_CHUNK_CODE = (
    _SAFE_TARGET_CODE
    + "import base64;"
    "offset=int(sys.argv[3]);length=int(sys.argv[4]);"
    "handle=target.open('rb');handle.seek(offset);data=handle.read(length);handle.close();"
    "sys.stdout.write(base64.b64encode(data).decode('ascii'))"
)


def _process_options() -> dict[str, Any]:
    if os.name == "nt":
        return {
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW
        }
    return {"start_new_session": True}


def _launch_directory(workspace: Path) -> Path:
    """Find the nearest host-readable ancestor outside the artifact root."""
    for candidate in workspace.parents:
        try:
            if candidate.is_dir():
                return candidate
        except OSError:
            continue
    raise ContractError("Codex artifact export has no usable launch directory.")


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=2)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        pass


class _AppServer:
    def __init__(self, workspace: Path):
        # The elevated sandbox can make the writable root and its immediate
        # parent unreadable to the host. Launch from the nearest usable ancestor;
        # the read-only child process receives the exact artifact root below.
        self.cwd = _launch_directory(workspace)
        command = codex_command() + ["app-server", "--listen", "stdio://"]
        windows_sandbox = _windows_sandbox_selection()
        if windows_sandbox:
            command.extend(["-c", f'windows.sandbox="{windows_sandbox}"'])
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=self.cwd,
            env=subprocess_environment("CODEX_HOME"),
            **_process_options(),
        )
        self.messages: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._stderr: list[str] = []
        threading.Thread(
            target=self._read_stdout,
            args=(self.process.stdout,),
            daemon=True,
        ).start()
        threading.Thread(
            target=self._read_stderr,
            args=(self.process.stderr,),
            daemon=True,
        ).start()

    def _read_stdout(self, stream: TextIO | None) -> None:
        try:
            if stream is None:
                return
            for line in stream:
                try:
                    value = json.loads(line)
                except (TypeError, ValueError):
                    continue
                if isinstance(value, dict):
                    self.messages.put(value)
        finally:
            self.messages.put(None)

    def _read_stderr(self, stream: TextIO | None) -> None:
        if stream is None:
            return
        total = 0
        for line in stream:
            if total >= 65_536:
                continue
            self._stderr.append(line[: 65_536 - total])
            total += len(self._stderr[-1])

    def send(self, value: dict[str, Any]) -> None:
        if self.process.stdin is None:
            raise ContractError("Codex artifact export could not start.")
        try:
            self.process.stdin.write(
                json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise ContractError("Codex artifact export could not start.") from exc

    def request(self, request_id: int, method: str, params: dict[str, Any],
                *, timeout: float = _RESPONSE_TIMEOUT_SECONDS) -> dict:
        self.send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
        deadline = time.monotonic() + min(timeout, _RESPONSE_TIMEOUT_SECONDS)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ContractError("Codex artifact export timed out.")
            try:
                message = self.messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise ContractError("Codex artifact export timed out.") from exc
            if message is None:
                raise ContractError("Codex artifact export stopped unexpectedly.")
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise ContractError("Codex artifact export was rejected by the sandbox.")
            result = message.get("result")
            if not isinstance(result, dict):
                raise ContractError("Codex artifact export returned an invalid response.")
            return result

    def close(self) -> None:
        if self.process.stdin is not None:
            try:
                self.process.stdin.close()
            except OSError:
                pass
        _stop_process(self.process)


def verify_codex_artifact(workspace: Path, relative: str, *, timeout: float = 20.0) -> None:
    """Validate a reported file using the same canonical policy inside Codex."""
    if (not isinstance(relative, str) or not relative or len(relative) > 500
            or Path(relative).is_absolute() or any(ord(char) < 32 for char in relative)
            or timeout <= 0):
        raise ContractError("Invalid Codex artifact verification request.")
    deadline = time.monotonic() + timeout

    def remaining():
        value = deadline - time.monotonic()
        if value <= 0:
            raise ContractError("Codex artifact verification deadline exhausted.")
        return value

    client = _AppServer(workspace.resolve())
    try:
        client.request(1, "initialize", {"clientInfo": {
            "name": "agentkit-artifact-check", "version": "0.1"}}, timeout=remaining())
        client.send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        result = client.request(2, "command/exec", {
            "command": [sys.executable, "-I", "-c", _CHECK_CODE,
                        str(workspace.resolve()), relative, _RUNTIME_ROOT],
            "cwd": str(client.cwd), "timeoutMs": max(1, min(_COMMAND_TIMEOUT_MS, int(remaining() * 1000))),
            "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
        }, timeout=remaining())
        if result.get("exitCode") != 0:
            raise ContractError("Reported artifact cannot be verified through the Codex sandbox.")
    finally:
        client.close()


def read_codex_artifact(
    workspace: Path,
    relative: str,
    *,
    max_bytes: int = MAX_ARTIFACT_BYTES,
) -> bytes:
    """Return one relative artifact via a bounded read-only Codex sandbox call."""
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
        or not isinstance(max_bytes, int)
        or max_bytes <= 0
        or max_bytes > MAX_ARTIFACT_BYTES
    ):
        raise ContractError("Invalid Codex artifact export request.")
    workspace = workspace.resolve()
    client = _AppServer(workspace)
    try:
        client.request(
            1,
            "initialize",
            {
                "clientInfo": {
                    "name": "agentkit-artifact-export",
                    "title": "AgentKit artifact export",
                    "version": "0.1",
                }
            },
        )
        client.send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        metadata_result = client.request(
            2,
            "command/exec",
            {
                "command": [
                    sys.executable,
                    "-I",
                    "-c",
                    _METADATA_CODE,
                    str(workspace),
                    relative,
                    str(max_bytes),
                    _RUNTIME_ROOT,
                ],
                "cwd": str(client.cwd),
                "timeoutMs": _COMMAND_TIMEOUT_MS,
                "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
            },
        )
        exit_code = metadata_result.get("exitCode")
        if exit_code == 43:
            raise ContractError(
                "Artifact exceeds the 2 MB download limit; open it in the workspace."
            )
        if exit_code != 0:
            raise ContractError("Artifact cannot be read through the Codex sandbox.")
        try:
            metadata = json.loads(metadata_result["stdout"])
            size = metadata["size"]
            expected_hash = metadata["sha256"]
            if (
                type(size) is not int
                or size < 0
                or size > max_bytes
                or not isinstance(expected_hash, str)
                or len(expected_hash) != 64
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ContractError("Codex artifact export returned invalid output.") from exc
        chunks: list[bytes] = []
        for request_id, offset in enumerate(range(0, size, _CHUNK_BYTES), start=3):
            result = client.request(
                request_id,
                "command/exec",
                {
                    "command": [
                        sys.executable,
                        "-I",
                        "-c",
                        _CHUNK_CODE,
                        str(workspace),
                        relative,
                        str(offset),
                        str(min(_CHUNK_BYTES, size - offset)),
                        _RUNTIME_ROOT,
                    ],
                    "cwd": str(client.cwd),
                    "timeoutMs": _COMMAND_TIMEOUT_MS,
                    "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
                },
            )
            encoded = result.get("stdout")
            if result.get("exitCode") != 0 or not isinstance(encoded, str):
                raise ContractError("Artifact cannot be read through the Codex sandbox.")
            if len(encoded) > ((_CHUNK_BYTES + 2) // 3) * 4:
                raise ContractError("Codex artifact export returned invalid output.")
            try:
                chunks.append(base64.b64decode(encoded, validate=True))
            except (TypeError, ValueError) as exc:
                raise ContractError("Codex artifact export returned invalid output.") from exc
        data = b"".join(chunks)
    finally:
        client.close()
    if len(data) != size or hashlib.sha256(data).hexdigest() != expected_hash:
        raise ContractError("Codex artifact export failed its integrity check.")
    return data
