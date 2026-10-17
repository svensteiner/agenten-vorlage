"""Immutable host-owned execution profiles for the local Cockpit only."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from agentkit.catalog import Catalog
from agentkit.contracts import ContractError
from agentkit.test_execution import TestExecutionPolicy
from agentkit.write_policy import WritePolicy


_PROFILE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_MAX_FILE_BYTES = 512_000


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate execution-profile key.")
        value[key] = item
    return value


@dataclass(frozen=True, slots=True)
class ExecutionProfile:
    id: str
    label: str
    agent: str
    company: str
    workspace: str
    backend: str
    write_policy: WritePolicy | None
    test_execution_policy: TestExecutionPolicy | None
    host_autonomous: bool
    sha256: str

    def metadata(self) -> dict[str, Any]:
        test = self.test_execution_policy
        return {
            "id": self.id,
            "label": self.label,
            "agent": self.agent,
            "company": self.company,
            "workspace": self.workspace,
            "backend": self.backend,
            "host_autonomous": self.host_autonomous,
            "sha256": self.sha256,
            "write_paths": list(self.write_policy.paths) if self.write_policy else [],
            "tests": ({"suite_files": len(test.test_paths),
                       "expected_test_count": test.expected_test_count,
                       "image_id": test.image_id,
                       "sha256": test.sha256} if test else None),
        }


class ExecutionProfileRegistry:
    """Load and bind operator profiles once; browser payloads carry only IDs."""

    def __init__(self, manager, path: Path):
        if getattr(manager, "public_mode", False):
            raise ContractError("Host execution profiles are not available in public mode.")
        self.manager = manager
        original = Path(path).expanduser().absolute()
        try:
            if original.is_symlink() or bool(getattr(original, "is_junction", lambda: False)()):
                raise ContractError("Execution-profile file must not be a link or junction.")
            resolved = original.resolve(strict=True)
            if resolved.is_symlink() or bool(getattr(resolved, "is_junction", lambda: False)()):
                raise ContractError("Execution-profile file must not be a link or junction.")
            if not resolved.is_file() or resolved.stat().st_size > _MAX_FILE_BYTES:
                raise ContractError("Execution-profile file must be a bounded regular file.")
            raw = resolved.read_bytes()
            document = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_pairs)
        except ContractError:
            raise
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            raise ContractError("Execution-profile file is unreadable or invalid JSON.") from exc
        if (type(document) is not dict or set(document) != {"version", "profiles"}
                or type(document["version"]) is not int or document["version"] != 1
                or type(document["profiles"]) is not list or len(document["profiles"]) > 100):
            raise ContractError("Execution-profile file does not match schema version 1.")
        profiles: dict[str, ExecutionProfile] = {}
        for row in document["profiles"]:
            profile = self._load_profile(row, resolved)
            if profile.id in profiles:
                raise ContractError("Execution profile IDs must be unique.")
            profiles[profile.id] = profile
        self.path = resolved
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self._profiles = MappingProxyType(profiles)

    def _load_profile(self, row: object, source_path: Path) -> ExecutionProfile:
        fields = {"id", "label", "agent", "workspace", "backend", "write_paths",
                  "test_manifest", "host_autonomous"}
        if type(row) is not dict or set(row) != fields:
            raise ContractError("Execution-profile fields do not match the host schema.")
        profile_id, label = row["id"], row["label"]
        if not isinstance(profile_id, str) or not _PROFILE_ID.fullmatch(profile_id):
            raise ContractError("Execution-profile ID is not canonical.")
        if not isinstance(label, str) or not label.strip() or len(label) > 120:
            raise ContractError("Execution-profile label must contain 1–120 characters.")
        if type(row["host_autonomous"]) is not bool:
            raise ContractError("host_autonomous must be boolean.")
        if not isinstance(row["agent"], str) or not isinstance(row["workspace"], str):
            raise ContractError("Profile agent and workspace bindings must be text.")
        if not isinstance(row["backend"], str) or row["backend"] not in self.manager.allowed_backends:
            raise ContractError("Profile backend is unavailable under server policy.")
        agent_path = self.manager._agent_path(row["agent"])
        workspace_path = self.manager._workspace_path(row["workspace"])
        agent = self.manager._agent_reference(agent_path)
        workspace = self.manager._workspace_reference(workspace_path)
        company = Catalog(agent_path).config["company"]

        write_paths = row["write_paths"]
        if type(write_paths) is not list or len(write_paths) > 4096:
            raise ContractError("write_paths must be a bounded list of exact relative files.")
        write_policy = WritePolicy(write_paths) if write_paths else None
        manifest = row["test_manifest"]
        test_policy = None
        if manifest is not None:
            if not isinstance(manifest, str) or not manifest or len(manifest) > 1000:
                raise ContractError("test_manifest must be a host path or null.")
            manifest_path = Path(manifest).expanduser()
            if not manifest_path.is_absolute():
                manifest_path = source_path.parent / manifest_path
            try:
                test_policy = TestExecutionPolicy.from_file(manifest_path)
            except (OSError, ValueError, TypeError) as exc:
                raise ContractError("Host test manifest is unavailable or invalid.") from exc
            try:
                test_policy.source_path.relative_to(workspace_path)
            except ValueError:
                pass
            else:
                raise ContractError("Test manifest must remain outside its bound workspace.")
        if row["host_autonomous"] and (write_policy is None or test_policy is None):
            raise ContractError("Autonomous profiles require an exact write allowlist and a pinned host test suite.")
        if write_policy is None and test_policy is None:
            raise ContractError("A profile must bind at least one host execution policy.")
        if write_policy is not None and row["backend"] not in {
            "demo", "codex", "deepseek", "api", "anthropic", "ollama"
        }:
            raise ContractError("Profile backend cannot enforce host write policy.")
        if test_policy is not None and row["backend"] not in {
            "codex", "deepseek", "api", "anthropic", "ollama"
        }:
            raise ContractError("Profile backend cannot enforce isolated host tests.")
        binding = {
            "version": 1, "id": profile_id, "label": label.strip(), "agent": agent,
            "company": company, "workspace": workspace, "backend": row["backend"],
            "write_policy_sha256": write_policy.sha256 if write_policy else "",
            "test_execution_policy_sha256": test_policy.sha256 if test_policy else "",
            "host_autonomous": row["host_autonomous"],
        }
        digest = hashlib.sha256(json.dumps(binding, ensure_ascii=False, sort_keys=True,
                                           separators=(",", ":")).encode("utf-8")).hexdigest()
        return ExecutionProfile(profile_id, label.strip(), agent, company, workspace,
                                row["backend"], write_policy, test_policy,
                                row["host_autonomous"], digest)

    def get(self, profile_id: str) -> ExecutionProfile:
        if not isinstance(profile_id, str) or not _PROFILE_ID.fullmatch(profile_id):
            raise ContractError("Invalid execution-profile ID.")
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ContractError("Unknown execution profile.")
        return profile

    def resolve(self, profile_id: str, agent: str, workspace: str, backend: str,
                *, expected_digest: str | None = None) -> ExecutionProfile:
        profile = self.get(profile_id)
        agent_path = self.manager._agent_path(agent)
        workspace_path = self.manager._workspace_path(workspace)
        actual = (self.manager._agent_reference(agent_path),
                  self.manager._workspace_reference(workspace_path), backend,
                  Catalog(agent_path).config["company"])
        expected = (profile.agent, profile.workspace, profile.backend, profile.company)
        if actual != expected:
            raise ContractError("Selected profile does not match this agent, workspace and backend.")
        if expected_digest is not None and expected_digest != profile.sha256:
            raise ContractError("Execution profile changed; this job cannot be rebound.")
        return profile

    def options_for(self, agent: str, workspace: str, backend: str) -> list[dict[str, Any]]:
        values = []
        for profile in self._profiles.values():
            try:
                self.resolve(profile.id, agent, workspace, backend)
            except ContractError:
                continue
            values.append(profile.metadata())
        return values

    def all_metadata(self) -> list[dict[str, Any]]:
        return [profile.metadata() for profile in self._profiles.values()]
