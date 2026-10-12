"""Explicit private-network Ollama transport; no cloud-provider fallback."""

from __future__ import annotations

import hashlib
import ipaddress
import io
import json
import os
from urllib.parse import urlsplit

from .api_backend import ApiBackend
from .contracts import ContractError


class OllamaBackend(ApiBackend):
    default_model = "qwen3-coder-next:latest"
    require_tool_observation = True
    repair_structured_report = True
    supported_tools = ApiBackend.supported_tools | {'search_file'}

    @staticmethod
    def _tool_specs(sandbox: str = "read-only") -> list[dict]:
        specs = ApiBackend._tool_specs(sandbox)
        for spec in specs:
            function = spec['function']
            if function['name'] == 'read_file':
                function['description'] = 'Read a bounded line range from a workspace text file. Default 100 lines, maximum 12000 characters. Use next_line to continue only relevant sections.'
                function['parameters']['properties'].update({
                    'start_line': {'type':'integer','minimum':1},
                    'max_lines': {'type':'integer','minimum':1,'maximum':200},
                })
        specs.append({'type':'function','function':{
            'name':'search_file',
            'description':'Find a literal text or function name in one workspace file. Returns up to 20 line numbers and short snippets; use read_file on the relevant lines instead of scanning entire large files.',
            'parameters':{'type':'object','properties':{'path':{'type':'string'},'text':{'type':'string'}},
                          'required':['path','text'],'additionalProperties':False},'strict':True}})
        return specs

    def _run_tool(self, name: str, arguments: dict, context: dict, timeout: float) -> str:
        if name not in {'read_file','search_file'}:
            return super()._run_tool(name, arguments, context, timeout)
        if name not in self.allowed_tools or timeout <= 0:
            raise ContractError('Read tool disabled or deadline exhausted.')
        if name == 'search_file':
            needle=arguments.get('text')
            if not isinstance(needle,str) or not 1 <= len(needle) <= 200 or set(arguments) != {'path','text'}:
                return json.dumps({'error':'invalid_search_arguments','hint':'Use exactly path and literal text (1..200 characters).'})
        start, count = arguments.get('start_line',1), arguments.get('max_lines',100)
        if (type(start) is not int or type(count) is not int or start < 1 or not 1 <= count <= 200
                or (name == 'read_file' and set(arguments) - {'path','start_line','max_lines'})):
            return json.dumps({'error':'invalid_read_range','hint':'Use path, optional integer start_line >= 1 and max_lines between 1 and 200. No other arguments. No file was read.'})
        target = self._workspace_path(context, arguments.get('path',''))
        try:
            if not target.is_file() or target.stat().st_size > 2_000_000:
                return json.dumps({'error':'file_missing_or_too_large'})
            with target.open('rb') as reader:
                raw = reader.read(2_000_001)
            if len(raw) > 2_000_000:
                return json.dumps({'error':'file_missing_or_too_large'})
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = raw.decode('cp1252')
        except (OSError,UnicodeDecodeError):
            return json.dumps({'error':'file_not_readable'})
        if name == 'search_file':
            matches, total_matches = [], 0
            for index,line in enumerate(io.StringIO(text),1):
                if needle in line:
                    total_matches += 1
                    if len(matches) < 20:
                        matches.append({'line':index,'snippet':line[:240].rstrip()})
            return json.dumps({'matches':matches,'total_matches':total_matches,'truncated':total_matches>20},ensure_ascii=False)
        selected, chars, total_lines, range_full = [], 0, 0, False
        for index,line in enumerate(io.StringIO(text),1):
            total_lines = index
            if index < start or index >= start + count or range_full:
                continue
            if chars + len(line) > 12000:
                if not selected:
                    return json.dumps({'error':'line_exceeds_read_budget','line':start})
                range_full = True
                continue
            selected.append(line)
            chars += len(line)
        if start > total_lines and not (start == 1 and not total_lines):
            return json.dumps({'error':'start_line_out_of_range','total_lines':total_lines})
        end = start - 1 + len(selected)
        return json.dumps({'path':arguments['path'],'start_line':start,'end_line':end,
                           'total_lines':total_lines,'next_line':end+1 if end < total_lines else None,
                           'truncated':end < total_lines,'content':''.join(selected)},ensure_ascii=False)

    def _chat(self, messages: list[dict], timeout: float, *, tools: list[dict] | None = None) -> dict:
        if tools:
            messages = [{"role": "system", "content":
                         "You must execute the assignment using actual tool calls. Never invent file contents, edits, test results or reviews. "
                         "The report JSON is only your FINAL response AFTER using the tools and observing their results. "
                         "Use search_file to locate symbols in large files, then read only the relevant line ranges. Do not scan entire large files or repeat identical reads. "
                         "The operator assignment authorizes work only within host permissions. A source document's live-action hold does not revoke explicitly authorized isolated code editing. "
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
