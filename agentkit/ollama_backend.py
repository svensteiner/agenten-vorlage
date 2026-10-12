"""Explicit private-network Ollama transport; no cloud-provider fallback."""

from __future__ import annotations

import hashlib
import ipaddress
import os
from urllib.parse import urlsplit

from .api_backend import ApiBackend
from .contracts import ContractError


class OllamaBackend(ApiBackend):
    default_model = "qwen3-coder-next:latest"
    require_tool_observation = True
    repair_structured_report = True

    def _chat(self, messages: list[dict], timeout: float, *, tools: list[dict] | None = None) -> dict:
        if tools:
            messages = [{"role": "system", "content":
                         "You must execute the assignment using actual tool calls. Never invent file contents, edits, test results or reviews. "
                         "The report JSON is only your FINAL response AFTER using the tools and observing their results. "
                         "For code changes use edit_file or write_file; for tests use run_pytest; for Git evidence use inspect_git. "
                         "A description of an action is not execution. Follow the approval boundary."}] + messages
        result = super()._chat(messages, timeout, tools=tools)
        if tools and not any(message.get("role") == "tool" for message in messages) and not result.get("tool_calls"):
            raise ContractError("Ollama returned a report without actual tool observations.")
        return result

    def __init__(self, model: str | None = None, *, base_url: str | None = None):
        endpoint = base_url if base_url is not None else os.environ.get("AGENTKIT_OLLAMA_BASE_URL", "")
        try:
            parsed = urlsplit(endpoint)
            address = ipaddress.ip_address(parsed.hostname or "")
            private_ranges = [ipaddress.ip_network(value) for value in
                              ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "::1/128")]
            valid = (parsed.scheme in {"http", "https"} and any(address in net for net in private_ranges)
                     and parsed.username is None and parsed.password is None
                     and "?" not in endpoint and "#" not in endpoint and parsed.path.rstrip("/") == "/v1"
                     and parsed.port is not None and 1 <= parsed.port <= 65535
                     and not any(char.isspace() or ord(char) < 32 for char in endpoint))
        except (TypeError, ValueError):
            valid = False
        if not valid:
            raise ContractError("Ollama requires an explicit private/loopback IP URL with port and /v1; no public hosts or credentials.")
        # Ollama ignores this compatibility value; it is not a credential.
        super().__init__(model or os.environ.get("AGENTKIT_OLLAMA_MODEL") or self.default_model,
                         api_key="ollama", base_url="https://" + parsed.netloc + "/v1", json_mode=True)
        self.base_url = endpoint.rstrip("/")
        self.name = "ollama:" + hashlib.sha256(self.base_url.encode()).hexdigest()[:24]
