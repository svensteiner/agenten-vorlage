"""Native Anthropic Messages transport with the shared bounded tool workflow."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .api_backend import ApiBackend
from .backends import _NoProviderRedirect
from .contracts import ContractError


class AnthropicBackend(ApiBackend):
    name = "anthropic"
    default_model = "claude-haiku-4-5-20251001"

    def __init__(self, model: str | None = None, *, api_key: str | None = None):
        key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
        super().__init__(model or os.environ.get("ANTHROPIC_MODEL") or self.default_model,
                         api_key=key, base_url="https://api.anthropic.com", json_mode=False)
        self.name = "anthropic"

    @staticmethod
    def _messages(messages: list[dict]) -> tuple[str, list[dict]]:
        system = []
        converted = []
        for message in messages:
            role = message.get("role")
            content = message.get("content") or ""
            if role == "system":
                system.append(content)
                continue
            if role == "tool":
                native_role = "user"
                blocks = [{"type": "tool_result", "tool_use_id": message["tool_call_id"], "content": content}]
            elif role in {"user", "assistant"}:
                native_role = role
                blocks = [{"type": "text", "text": content}] if content else []
                for call in message.get("tool_calls", []):
                    function = call["function"]
                    args = function.get("arguments", {})
                    if isinstance(args, str):
                        args = json.loads(args)
                    if not isinstance(args, dict):
                        raise ContractError("Anthropic tool input must be an object.")
                    blocks.append({"type": "tool_use", "id": call["id"],
                                   "name": function["name"], "input": args})
            else:
                raise ContractError("Unsupported Anthropic message role.")
            if converted and converted[-1]["role"] == native_role:
                converted[-1]["content"].extend(blocks)
            else:
                converted.append({"role": native_role, "content": blocks})
        return "\n\n".join(system), converted

    def _chat(self, messages: list[dict], timeout: float, *, tools: list[dict] | None = None) -> dict:
        try:
            system, converted = self._messages(messages)
        except (KeyError, TypeError, ValueError) as exc:
            raise ContractError("Anthropic message conversion failed.") from exc
        payload = {"model": self.model, "max_tokens": 4096, "messages": converted}
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [{"name": item["function"]["name"],
                                 "description": item["function"].get("description", ""),
                                 "input_schema": item["function"]["parameters"]} for item in tools]
            payload["tool_choice"] = {"type": "auto"}
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=json.dumps(payload).encode("utf-8"),
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.build_opener(_NoProviderRedirect()).open(request, timeout=timeout) as response:
                raw = response.read(1_000_001)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Anthropic API returned HTTP {exc.code}; inspect provider configuration.") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError("Anthropic API request failed; inspect network/provider configuration.") from exc
        if len(raw) > 1_000_000:
            raise ContractError("Anthropic response exceeds the size limit.")
        try:
            envelope = json.loads(raw)
            if envelope.get("stop_reason") == "max_tokens":
                raise ContractError("Anthropic response reached its token limit; no action was executed.")
            blocks = envelope["content"]
            stop_reason = envelope.get("stop_reason")
            if stop_reason not in {"end_turn", "tool_use", "stop_sequence"}:
                raise ValueError("unsupported stop reason")
            if not isinstance(blocks, list):
                raise ValueError("missing content blocks")
            text = []
            calls = []
            for block in blocks:
                if block["type"] == "text":
                    text.append(block["text"])
                elif block["type"] == "tool_use":
                    if not isinstance(block["input"], dict):
                        raise ValueError("invalid tool input")
                    calls.append({"id": block["id"], "type": "function", "function": {
                        "name": block["name"], "arguments": json.dumps(block["input"]),
                    }})
                else:
                    raise ValueError("unsupported content block")
            result = {"role": "assistant", "content": "\n".join(text)}
            if bool(calls) != (stop_reason == "tool_use"):
                raise ValueError("stop reason does not match tool content")
            if calls:
                result["tool_calls"] = calls
            return result
        except (KeyError, TypeError, ValueError) as exc:
            raise ContractError("Anthropic returned an invalid message.") from exc
