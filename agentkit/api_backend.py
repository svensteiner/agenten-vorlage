"""Explicit provider-independent Chat Completions adapter for local agent runs."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from .backends import DeepSeekBackend, _process_result, subprocess_environment
from .contracts import ContractError


class ApiBackend(DeepSeekBackend):
    """Reuse bounded tool execution without inheriting DeepSeek credentials."""

    supported_tools = DeepSeekBackend.supported_tools | {"inspect_git"}

    @staticmethod
    def _tool_specs(sandbox: str = "read-only") -> list[dict]:
        return DeepSeekBackend._tool_specs(sandbox) + [{
            "type": "function", "function": {
                "name": "inspect_git",
                "description": "Read actual Git status and diff HEAD for the workspace root. No mutation. Reports unavailable or truncated evidence explicitly.",
                "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                "strict": True,
            },
        }]

    def _run_tool(self, name: str, arguments: dict, context: dict, timeout: float) -> str:
        if name != "inspect_git":
            return super()._run_tool(name, arguments, context, timeout)
        if name not in self.allowed_tools or arguments or timeout <= 0:
            raise ContractError("Invalid Git inspection request.")
        workspace = Path(context["workspace"]).resolve()
        if not workspace.is_dir():
            raise ContractError("Git inspection workspace does not exist.")
        executable = shutil.which("git")
        if not executable:
            return json.dumps({"status": "unavailable", "reason": "git_not_installed"})
        environment = subprocess_environment()
        environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                           GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
        command = [executable, "-c", "core.fsmonitor=false", "-c", "core.pager=cat"]
        deadline = time.monotonic() + timeout
        def run(args):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            return _process_result(command + args, "", workspace, remaining, env=environment)
        try:
            code, root, _ = run(["rev-parse", "--show-toplevel"])
            if code or Path(root.strip()).resolve() != workspace:
                return json.dumps({"status": "unavailable", "reason": "workspace_is_not_git_root"})
            status_code, status, _ = run(["status", "--porcelain=v1", "--untracked-files=normal"])
            diff_code, diff, _ = run(["diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--ignore-submodules=all", "HEAD", "--"])
        except subprocess.TimeoutExpired:
            return json.dumps({"status": "unavailable", "reason": "git_inspection_timeout"})
        if status_code or diff_code:
            return json.dumps({"status": "unavailable", "reason": "git_inspection_failed"})
        if self.api_key:
            status = status.replace(self.api_key, "[REDACTED]")
            diff = diff.replace(self.api_key, "[REDACTED]")
        return json.dumps({"status": "ok", "git_status": status[:12000], "diff_head": diff[:24000],
                           "truncated": len(status) > 12000 or len(diff) > 24000}, ensure_ascii=False)

    def __init__(self, model: str | None = None, *, api_key: str | None = None,
                 base_url: str | None = None, json_mode: bool | None = None):
        selected_key = api_key if api_key is not None else os.environ.get("AGENTKIT_API_KEY", "")
        selected_url = base_url if base_url is not None else os.environ.get("AGENTKIT_API_BASE_URL", "")
        selected_model = model if model is not None else os.environ.get("AGENTKIT_API_MODEL", "")
        if not all(isinstance(value, str) and value.strip()
                   for value in (selected_key, selected_url, selected_model)):
            raise ContractError("API provider requires an explicit key, HTTPS base URL and model.")
        if (not selected_key.isascii() or len(selected_key) > 512
                or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in selected_key)):
            raise ContractError("API key must be 1–512 ASCII characters without whitespace or controls.")
        if len(selected_model) > 200 or any(ord(char) < 32 or ord(char) == 127 for char in selected_model):
            raise ContractError("API model is invalid.")
        mode = os.environ.get("AGENTKIT_API_JSON_MODE", "on")
        if json_mode is None and mode not in {"on", "off"}:
            raise ContractError("AGENTKIT_API_JSON_MODE must be on or off.")
        self.json_mode = mode == "on" if json_mode is None else json_mode
        if not isinstance(self.json_mode, bool):
            raise ContractError("API JSON mode must be a boolean.")
        super().__init__(selected_model.strip(), api_key=selected_key, base_url=selected_url)
        # The engine binds checkpoints and approvals to this identity. Changing
        # endpoints must not resume another provider's pending execution.
        endpoint_digest = hashlib.sha256(self.base_url.encode("utf-8")).hexdigest()[:24]
        self.name = f"api:{endpoint_digest}"

    def _chat(self, messages: list[dict], timeout: float, *, tools: list[dict] | None = None) -> dict:
        try:
            return super()._chat(messages, timeout, tools=tools)
        except (RuntimeError, ContractError) as exc:
            raise type(exc)(str(exc).replace("DeepSeek", "Configured provider")) from exc
