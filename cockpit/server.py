"""Small local web cockpit for the AgentKit engine."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import copy
import shutil
import sys
import threading
import tempfile
import time
import uuid
import webbrowser
from datetime import datetime, timezone
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse, parse_qs, quote

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEMPLATE_ROOT))

from agentkit.backends import CodexBackend, DeepSeekBackend, DemoBackend, codex_readiness  # noqa: E402
from agentkit.api_backend import ApiBackend  # noqa: E402
from agentkit.anthropic_backend import AnthropicBackend  # noqa: E402
from agentkit.ollama_backend import OllamaBackend  # noqa: E402
from agentkit.approvals import safe_workspace_path  # noqa: E402
from agentkit.catalog import Catalog  # noqa: E402
from agentkit.codex_artifacts import read_codex_artifact  # noqa: E402
from agentkit.contracts import ContractError  # noqa: E402
from agentkit.engine import Engine  # noqa: E402
from agentkit.scaffold import create  # noqa: E402
from agentkit.contracts import LIBRARY, read_json  # noqa: E402
from agentkit.storage import lock, save  # noqa: E402
from cockpit.conversations import Conversations  # noqa: E402
from cockpit.providers import ProviderSettings  # noqa: E402
from cockpit.assistant_settings import AssistantSettings  # noqa: E402
from cockpit.assistant_instructions import (  # noqa: E402
    InstructionConflict,
    read_document,
    replace_document,
    validate_revision,
    validate_text,
)
from cockpit.github_connector import preview_file  # noqa: E402


@dataclass
class Job:
    job_id: str
    payload: dict[str, Any]
    status: str = "queued"
    result: dict[str, Any] | None = None
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    thread: threading.Thread | None = field(default=None, repr=False)

    def public(self) -> dict[str, Any]:
        result = self.result
        return {
            "job_id": self.job_id,
            "status": self.status,
            "agent": self.payload.get("agent"),
            "backend": self.payload.get("backend"),
            "workspace": self.payload.get("workspace"),
            "task": self.payload.get("task"),
            "result": result,
            "error": self.error,
            "created_at": self.created_at,
            "model": self.payload.get("model", ""),
            "parent_job_id": self.payload.get("parent_job_id"),
            "conversation_id": self.payload.get("conversation_id"),
            "require_approvals": self.payload.get("require_approvals", False),
            "assistant_revision": self.payload.get("core_sha256", ""),
        }


class JobManager:
    def __init__(
        self,
        template_root: Path = TEMPLATE_ROOT,
        state_dir: Path | None = None,
        max_active: int = 4,
        *,
        agent_roots: tuple[Path, ...] | None = None,
        generated_root: Path | None = None,
        workspace_root: Path | None = None,
        public_mode: bool = False,
        allowed_backends: set[str] | frozenset[str] | None = None,
        provider_api_key: str | None = None,
        worker_semaphore: threading.BoundedSemaphore | None = None,
        mutation_writer: Callable[[Path, bytes], None] | None = None,
        storage_writer: Callable[[Path, bytes], None] | None = None,
        coordination_reserver: Callable[[Path, Path], Any] | None = None,
        default_workspace: Path | None = None,
        preferred_agent: str = "",
        preferred_backend: str = "",
        starter_task: str = "",
    ):
        self.template_root = template_root.resolve()
        self.agent_roots = tuple(
            root.resolve() for root in (agent_roots or (
                self.template_root / "agents",
                self.template_root / "generated",
            ))
        )
        if not self.agent_roots:
            raise ValueError("At least one assistant root is required.")
        self.generated_root = (generated_root or self.template_root / "generated").resolve()
        if self.generated_root not in self.agent_roots:
            raise ValueError("The generated assistant root must be a registered assistant root.")
        self.workspace_root = workspace_root.resolve() if workspace_root is not None else None
        self.public_mode = bool(public_mode)
        if self.public_mode and self.workspace_root is None:
            raise ValueError("Public mode requires a server-controlled workspace root.")
        if default_workspace is not None and self.public_mode:
            raise ValueError("Public mode controls its own default workspace.")
        self.default_workspace = default_workspace.resolve() if default_workspace else None
        if self.default_workspace is not None and not self.default_workspace.is_dir():
            raise ValueError("The configured default workspace must be an existing directory.")
        defaults = {"demo", "codex", "deepseek"} if self.public_mode else {"demo", "codex", "deepseek", "api", "anthropic", "ollama"}
        self.allowed_backends = frozenset(allowed_backends or defaults)
        if not self.allowed_backends or not self.allowed_backends <= {"demo", "codex", "deepseek", "api", "anthropic", "ollama"}:
            raise ValueError("allowed_backends contains an unsupported backend.")
        if self.public_mode and self.allowed_backends & {"api", "anthropic", "ollama"}:
            raise ValueError("Custom API providers are available only in local mode.")
        if preferred_agent and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", preferred_agent):
            raise ValueError("preferred_agent must be a canonical assistant id.")
        if preferred_backend and preferred_backend not in self.allowed_backends:
            raise ValueError("preferred_backend must be enabled.")
        if not isinstance(starter_task, str) or len(starter_task) > 12_000:
            raise ValueError("starter_task must be bounded text.")
        self.preferred_agent = preferred_agent
        self.preferred_backend = preferred_backend
        self.starter_task = starter_task.strip()
        if provider_api_key is not None and (
            not isinstance(provider_api_key, str)
            or not provider_api_key.strip()
            or len(provider_api_key) > 500
        ):
            raise ValueError("provider_api_key must be bounded non-empty text.")
        self._provider_api_key = provider_api_key.strip() if provider_api_key is not None else None
        self._worker_semaphore = worker_semaphore
        self._mutation_writer = mutation_writer
        self._storage_writer = storage_writer
        self._coordination_reserver = coordination_reserver
        self.state_dir = (state_dir or self.template_root / "cockpit" / ".runs").resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.providers = ProviderSettings(self.state_dir)
        self.anthropic_provider = ProviderSettings(self.state_dir, "anthropic")
        self.assistant_settings = AssistantSettings(
            self.state_dir,
            storage_writer=self._storage_writer,
        )
        self.jobs: dict[str, Job] = {}
        self.max_active = max_active
        self._lock = threading.Lock()
        self._load()

    def _job_file(self, job_id: str) -> Path:
        return self.state_dir / f"{job_id}.json"

    def _persist(self, job: Job) -> None:
        payload = {
            "job_id": job.job_id,
            "payload": job.payload,
            "status": job.status,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at,
        }
        target = self._job_file(job.job_id)
        if self._storage_writer is not None:
            save(target, payload, writer=self._storage_writer)
            return
        fd, temporary = tempfile.mkstemp(prefix=f".{job.job_id}.", suffix=".tmp", dir=self.state_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _load(self) -> None:
        completed = 0
        for path in sorted(self.state_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            job = self._restore(path)
            if job and job.status == "completed":
                completed += 1
                if completed > 100:
                    self.jobs.pop(job.job_id, None)

    def _restore(self, path: Path) -> Job | None:
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            job_id = saved["job_id"]
            payload = saved["payload"]
            if not isinstance(job_id, str) or not re.fullmatch(r"[0-9a-f]{32}", job_id) or path.stem != job_id or not isinstance(payload, dict):
                return None
            job = Job(job_id, payload, saved.get("status", "blocked"), saved.get("result"), saved.get("error", ""))
            job.created_at = saved.get("created_at", datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat())
            if job.status in {"queued", "running"}:
                job.status = "blocked"
                job.error = "Cockpit wurde neu gestartet; Fortsetzung benötigt Feedback und Bestätigung."
                self._persist(job)
            self.jobs[job_id] = job
            return job
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def _set_status(self, job: Job, status: str, *, error: str | None = None) -> None:
        with self._lock:
            job.status = status
            if error is not None:
                job.error = error
            self._persist(job)

    def _agent_path(self, value: str) -> Path:
        if getattr(self, "public_mode", False):
            if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", value):
                raise ContractError("Assistant must be a canonical assistant id.")
            matches: list[Path] = []
            for root in self.agent_roots:
                candidate = root / value
                if candidate.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(candidate)):
                    continue
                try:
                    resolved = candidate.resolve()
                    if resolved.parent != root or not (resolved / "agent.json").is_file():
                        continue
                    if Catalog(resolved).config["id"] == value:
                        matches.append(resolved)
                except (ContractError, OSError, ValueError):
                    continue
            if len(matches) != 1:
                raise ContractError("Assistant id is missing or ambiguous.")
            return matches[0]
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = self.template_root / candidate
        candidate = candidate.resolve()
        if not any(candidate.is_relative_to(root.resolve()) for root in self.agent_roots):
            raise ContractError("Agent must be inside agents/ or generated/.")
        if not (candidate / "agent.json").is_file():
            raise ContractError("Agent pack is missing agent.json.")
        return candidate

    def _agent_reference(self, path: Path) -> str:
        return Catalog(path).config["id"] if self.public_mode else str(path)

    def _workspace_reference(self, path: Path) -> str:
        if not self.public_mode:
            return str(path)
        assert self.workspace_root is not None
        relative = path.relative_to(self.workspace_root)
        if len(relative.parts) != 1:
            raise ContractError("Workspace must be a registered top-level workspace.")
        return relative.as_posix()

    def _instruction_agent(self, value: str) -> Path:
        """Resolve only a registered, direct child assistant pack."""
        agent = self._agent_path(value)
        if not any(agent.parent.resolve() == root.resolve() for root in self.agent_roots):
            raise ContractError("Assistant path is not a registered top-level assistant pack.")
        try:
            Catalog(agent)
        except (ContractError, OSError, ValueError) as exc:
            raise ContractError("Assistant pack is invalid.") from exc
        return agent

    def _instruction_result(self, agent: Path, document) -> dict[str, Any]:
        config = Catalog(agent).config
        return {"agent": self._agent_reference(agent), "id": config["id"], "text": document.text, "revision": document.revision}

    def _instruction_guard(self, agent: Path) -> None:
        """Reject edits while an old run could still reread SOUL.md."""
        canonical = str(agent.resolve())
        config = Catalog(agent).config
        agent_id = config["id"]
        max_context = int(config["limits"]["max_context_chars"])
        allowed_statuses = {"queued", "running", "blocked", "completed", "error", "awaiting_approval"}

        def valid_snapshot(value: object) -> bool:
            if not isinstance(value, str) or not value.strip() or len(value) > max_context:
                return False
            try:
                value.encode("utf-8", "strict")
            except UnicodeError:
                return False
            return True

        def validate_snapshot(record: dict, *, required: bool) -> None:
            if "core_snapshot" not in record:
                if required:
                    raise InstructionConflict("Instruction edit requires recovery of a legacy run without a valid core snapshot.")
                return
            snapshot = record.get("core_snapshot")
            if not valid_snapshot(snapshot):
                raise InstructionConflict("Instruction edit is blocked by an invalid run instruction snapshot.")
            digest = record.get("core_sha256")
            if digest is not None:
                if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise InstructionConflict("Instruction edit is blocked by an invalid run instruction hash.")
                if hashlib.sha256(snapshot.encode("utf-8")).hexdigest() != digest:
                    raise InstructionConflict("Instruction edit is blocked by an inconsistent run instruction hash.")

        def check_state(path: Path) -> None:
            try:
                state = read_json(path)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                raise InstructionConflict("Instruction edit is blocked by malformed run state; recover the run first.") from exc
            if not isinstance(state, dict):
                raise InstructionConflict("Instruction edit is blocked by malformed run state; recover the run first.")
            if path.parent.name != state.get("run_id") or not re.fullmatch(r"[0-9a-f]{32}", str(state.get("run_id", ""))):
                raise InstructionConflict("Instruction edit is blocked by an inconsistent run identity.")
            if state.get("agent") != agent_id:
                raise InstructionConflict("Instruction edit is blocked by an inconsistent assistant binding.")
            status = state.get("status")
            if status not in allowed_statuses:
                raise InstructionConflict("Instruction edit is blocked by an unknown run status.")
            validate_snapshot(state, required=status != "completed")

        # Job records are globally stored.  Parse only records that can be
        # positively bound to another assistant.  A canonical job filename
        # with malformed or missing binding is fail-closed because it may be
        # an older run for this pack.
        for path in self.state_dir.glob("*.json"):
            if not re.fullmatch(r"[0-9a-f]{32}", path.stem):
                continue
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
                payload = saved.get("payload") if isinstance(saved, dict) else None
                if not isinstance(payload, dict) or not isinstance(payload.get("agent"), str):
                    raise InstructionConflict("Instruction edit is blocked by a job with unknown assistant binding.")
                try:
                    payload_agent = str(self._agent_path(payload["agent"]))
                except (ContractError, OSError) as exc:
                    raise InstructionConflict("Instruction edit is blocked by a job with unknown assistant binding.") from exc
                bound = payload_agent == canonical
                if not bound:
                    continue
                if saved.get("job_id") != path.stem:
                    raise InstructionConflict("Instruction edit is blocked by an inconsistent job identity.")
                status = saved.get("status")
                if status not in allowed_statuses:
                    raise InstructionConflict("Instruction edit is blocked by an unknown job status.")
                validate_snapshot(payload, required=status != "completed")
                run_id = payload.get("run_id", "")
                if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{32}", run_id):
                    raise InstructionConflict("Instruction edit is blocked by an inconsistent run identity.")
                checkpoint = agent / ".runs" / run_id / "state.json"
                if checkpoint.exists():
                    check_state(checkpoint)
            except InstructionConflict:
                raise
            except (OSError, ValueError, TypeError, KeyError) as exc:
                raise InstructionConflict("Instruction edit is blocked by malformed job state; recover the run first.") from exc

        runs = agent / ".runs"
        if not runs.is_dir():
            return
        for checkpoint in runs.glob("*/state.json"):
            check_state(checkpoint)

    def get_instructions(self, agent: str) -> dict[str, Any]:
        with self._lock:
            path = self._instruction_agent(agent)
            with lock(path / ".instructions.lock"):
                return self._instruction_result(path, read_document(path))

    def _capture_core_locked(self, path: Path) -> dict[str, str]:
        document = read_document(path)
        core = Catalog(path).core()
        try:
            core.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise ContractError("Assistant catalog is not valid UTF-8.") from exc
        return {
            "core_snapshot": core,
            "core_sha256": hashlib.sha256(core.encode("utf-8")).hexdigest(),
            "revision": document.revision,
        }

    def capture_core(self, agent: str) -> dict[str, str]:
        """Capture the complete portable prompt under the same pack lock."""
        with self._lock:
            path = self._instruction_agent(agent)
            with lock(path / ".instructions.lock"):
                return self._capture_core_locked(path)

    def update_instructions(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or set(payload) != {"agent", "text", "revision"}:
            raise ContractError("Instruction update must contain exactly agent, text and revision.")
        path_value = payload["agent"]
        if not isinstance(path_value, str):
            raise ContractError("agent must be text.")
        path = self._instruction_agent(path_value)
        # Validate before taking locks so malformed requests have no side
        # effects and never create a lock file for an invalid edit.
        _, encoded = validate_text(payload["text"])
        validate_revision(payload["revision"])
        with self._lock:
            with lock(path / ".instructions.lock"):
                current = read_document(path)
                if current.raw == encoded:
                    return self._instruction_result(path, current)
                self._instruction_guard(path)
                return self._instruction_result(
                    path,
                    replace_document(
                        path,
                        payload["text"],
                        payload["revision"],
                        storage_writer=self._storage_writer,
                    ),
                )

    def _workspace_path(self, value: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ContractError("Workspace is required.")
        if getattr(self, "public_mode", False):
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
                raise ContractError("Workspace must be a canonical workspace id.")
            assert self.workspace_root is not None
            candidate = self.workspace_root / value
            if candidate.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(candidate)):
                raise ContractError("Workspace links are not allowed in public mode.")
            workspace = candidate.resolve()
            if workspace.parent != self.workspace_root or not workspace.is_dir():
                raise ContractError("Workspace must be a registered top-level workspace.")
            return workspace
        workspace = Path(value).expanduser().resolve()
        if not workspace.is_dir():
            raise ContractError("Workspace must be an existing directory.")
        return workspace

    def agents(self, *, include_archived: bool = False) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for root in self.agent_roots:
            if not root.is_dir():
                continue
            for agent_json in sorted(root.glob("*/agent.json")):
                try:
                    catalog = Catalog(agent_json.parent)
                except (ContractError, OSError, ValueError):
                    continue
                config = catalog.config
                archived = self.assistant_settings.archived(agent_json.parent)
                if archived and not include_archived:
                    continue
                found.append({
                        "id": config["id"],
                        "company": config["company"],
                        "profile": config["profile"],
                        "path": self._agent_reference(agent_json.parent.resolve()),
                        "roles": len(config["roles"]),
                        "skills": len(catalog.skills),
                        "archived": archived,
                    })
        return found

    def create_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = payload.get("name", "")
        profile = payload.get("profile", "developer")
        company = payload.get("company", "Local")
        instructions = payload.get("instructions", "")
        if not all(isinstance(item, str) for item in (name, profile, company, instructions)):
            raise ContractError("Assistant fields must be text.")
        if len(instructions) > 10_000:
            raise ContractError("Instructions are too large.")
        with self._lock:
            target = create(
                self.generated_root / name,
                profile,
                name,
                company,
                storage_writer=self._storage_writer,
            )
            try:
                if instructions.strip():
                    soul = target / "SOUL.md"
                    addition = "\n\n## Owner instructions\n\n" + instructions.strip() + "\n"
                    with lock(target / ".instructions.lock"):
                        if self._storage_writer is None:
                            with soul.open("a", encoding="utf-8") as handle:
                                handle.write(addition)
                        else:
                            self._storage_writer(soul, soul.read_bytes() + addition.encode("utf-8"))
            except Exception:
                shutil.rmtree(target, ignore_errors=True)
                raise
        reference = self._agent_reference(target)
        return next(agent for agent in self.agents(include_archived=True) if agent["path"] == reference)

    def archive_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or set(payload) != {"agent", "archived"}:
            raise ContractError("Archive request must contain agent and archived.")
        if not isinstance(payload["agent"], str) or not isinstance(payload["archived"], bool):
            raise ContractError("agent must be text and archived must be boolean.")
        agent = self._agent_path(payload["agent"])
        registered = next((item for item in self.agents(include_archived=True)
                           if self._agent_path(item["path"]) == agent), None)
        if registered is None:
            raise ContractError("Assistant path is not a registered top-level assistant pack.")
        self.assistant_settings.set_archived(agent, payload["archived"])
        registered = dict(registered)
        registered["archived"] = payload["archived"]
        return registered

    def _run(self, job: Job) -> None:
        try:
            self._set_status(job, "running")
            agent_path = self._agent_path(job.payload["agent"])
            workspace = self._workspace_path(job.payload["workspace"])
            backend_name = job.payload.get("backend", "demo")
            if backend_name not in self.allowed_backends:
                raise ContractError("Backend is disabled by the execution isolation policy.")
            model = job.payload.get("model") or None
            backend_type = {
                "demo": DemoBackend,
                "codex": CodexBackend,
                "deepseek": DeepSeekBackend,
                "api": ApiBackend,
                "anthropic": AnthropicBackend,
                "ollama": OllamaBackend,
            }.get(backend_name)
            if backend_type is None:
                raise ContractError(f"Unknown backend: {backend_name}")
            if backend_name == "deepseek":
                key = self._provider_api_key if self.public_mode else self.providers.api_key()
                if not key:
                    raise ContractError("DeepSeek ist nicht eingerichtet. Bitte Provider-Einstellungen öffnen.")
                allowed_tools = (
                    {"list_files", "read_file", "write_file", "edit_file"}
                    if self.public_mode else None
                )
                backend_kwargs: dict[str, Any] = {
                    "api_key": key,
                    "base_url": "https://api.deepseek.com",
                }
                if allowed_tools is not None:
                    backend_kwargs["allowed_tools"] = allowed_tools
                backend = DeepSeekBackend(model, **backend_kwargs)
            elif backend_name == "anthropic":
                backend = AnthropicBackend(model, api_key=self.anthropic_provider.api_key())
            else:
                backend = DemoBackend() if backend_name == "demo" else backend_type(model)
            run_id = job.payload["run_id"]
            if not re.fullmatch(r"[0-9a-f]{32}", run_id):
                raise ContractError("Invalid run identity.")
            checkpoint = agent_path / ".runs" / run_id
            run_dir = checkpoint if (checkpoint / "state.json").is_file() else None
            result = Engine(agent_path, workspace, backend,
                            require_approvals=backend_name in {"codex", "deepseek", "api", "anthropic", "ollama"} or job.payload.get("require_approvals", False),
                            core_snapshot=job.payload.get("core_snapshot"),
                            mutation_writer=self._mutation_writer,
                            state_writer=self._storage_writer,
                            coordination_reserver=self._coordination_reserver).run(
                job.payload.get("execution_task", job.payload["task"]),
                run_dir=run_dir,
                new_run_id=run_id if run_dir is None else None,
                feedback=str(job.payload.get("feedback", "")),
                acknowledge_interruption=bool(job.payload.get("acknowledge_interruption", False)),
                approval_id=job.payload.get("approval_id", ""),
                approval_decision=job.payload.get("approval_decision", ""),
            )
            with self._lock:
                job.result = result
                job.status = result.get("status", "blocked")
                job.payload.pop("approval_id", None)
                job.payload.pop("approval_decision", None)
                self._persist(job)
        except Exception as exc:
            self._set_status(job, "error", error=f"{type(exc).__name__}: {exc}")

    def start(self, payload: dict[str, Any], *, conversation_id: str = "", execution_task: str = "",
              core_snapshot: str | None = None) -> Job:
        if "core_snapshot" in payload:
            raise ContractError("core_snapshot is internal and cannot be supplied in a client payload.")
        if core_snapshot is not None and not isinstance(core_snapshot, str):
            raise ContractError("core_snapshot must be text.")
        if not isinstance(payload.get("require_approvals", False), bool):
            raise ContractError("require_approvals must be boolean.")
        for key in ("agent", "workspace", "task", "backend", "model", "parent_job_id", "request_id"):
            if key in payload and not isinstance(payload[key], str):
                raise ContractError(f"{key} must be text.")
        backend_name = payload.get("backend", "demo")
        # Codex and DeepSeek own an approval-enabled execution path. Demo
        # remains opt-in so existing fixture jobs can still run unattended.
        require_approvals = backend_name in {"codex", "deepseek", "api", "anthropic", "ollama"} or payload.get("require_approvals", False)
        if backend_name not in {"demo", "codex", "deepseek", "api", "anthropic", "ollama"}:
            raise ContractError("Unknown backend.")
        if backend_name not in self.allowed_backends:
            raise ContractError("Backend is disabled by the execution isolation policy.")
        if len(payload.get("model", "")) > 200:
            raise ContractError("Model name is too large.")
        task = payload.get("task")
        if not isinstance(task, str) or not task.strip():
            raise ContractError("Task must not be empty.")
        if len(task) > 20_000:
            raise ContractError("Task is too large.")
        agent_path = self._agent_path(str(payload.get("agent", "")))
        workspace_path = self._workspace_path(str(payload.get("workspace", "")))
        agent_reference = self._agent_reference(agent_path)
        workspace_reference = self._workspace_reference(workspace_path)
        request_id = payload.get("request_id", "")
        if request_id and not re.fullmatch(r"[0-9a-f]{32}", request_id):
            raise ContractError("request_id must be 32 lowercase hexadecimal characters.")
        job_id = request_id or uuid.uuid4().hex
        with self._lock:
            existing = self.jobs.get(job_id) or self._restore(self._job_file(job_id))
            if existing:
                if core_snapshot is not None and existing.payload.get("core_snapshot") != core_snapshot:
                    raise ContractError("request_id was already used with a different assistant instruction snapshot.")
                # Retries return the durable original snapshot; they never
                # reread SOUL.md after the first reservation.
                fields = ("agent", "workspace", "backend", "model", "task", "parent_job_id", "conversation_id")
                proposed = {
                    "agent": agent_reference, "workspace": workspace_reference,
                    "backend": str(payload.get("backend", "demo")), "model": str(payload.get("model", "")),
                    "task": task.strip(), "parent_job_id": payload.get("parent_job_id", ""),
                    "conversation_id": conversation_id,
                }
                mismatch = any(existing.payload.get(key, "") != proposed.get(key, "") for key in fields)
                mismatch = mismatch or existing.payload.get("require_approvals", False) != require_approvals
                if conversation_id or execution_task:
                    mismatch = mismatch or existing.payload.get("execution_task", "") != execution_task
                if mismatch:
                    raise ContractError("request_id was already used for a different task.")
                return existing
            if self._job_file(job_id).exists():
                raise ContractError("This request has unreadable local state; no new task was started.")
            with lock(agent_path / ".instructions.lock"):
                if core_snapshot is None:
                    snapshot = self._capture_core_locked(agent_path)["core_snapshot"]
                else:
                    snapshot = core_snapshot
                if not snapshot.strip():
                    raise ContractError("Assistant instructions must not be blank.")
                try:
                    snapshot_bytes = snapshot.encode("utf-8", "strict")
                except UnicodeError as exc:
                    raise ContractError("Assistant instruction snapshot must be valid UTF-8.") from exc
                if len(snapshot) > 80_000:
                    raise ContractError("Assistant instruction snapshot is too large.")
                job = Job(
                    job_id,
                    {
                        "agent": agent_reference,
                        "run_id": uuid.uuid4().hex,
                        "backend": str(payload.get("backend", "demo")),
                        "model": str(payload.get("model", "")),
                        "workspace": workspace_reference,
                        "task": task.strip(),
                        "parent_job_id": payload.get("parent_job_id", ""),
                        "conversation_id": conversation_id,
                        "require_approvals": require_approvals,
                        "core_snapshot": snapshot,
                        "core_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
                    },
                )
                if execution_task:
                    job.payload["execution_task"] = execution_task
                if payload.get("parent_job_id"):
                    parent_id = payload["parent_job_id"]
                    if not re.fullmatch(r"[0-9a-f]{32}", parent_id):
                        raise ContractError("Invalid parent job identity.")
                    parent = self.jobs.get(parent_id) or self._restore(self._job_file(parent_id))
                    if parent is None or parent.status != "completed":
                        raise ContractError("Follow-up requires a completed parent task.")
                    if any(parent.payload.get(key) != job.payload.get(key) for key in ("agent", "workspace", "backend")):
                        raise ContractError("Follow-up cannot cross agent, workspace or backend boundaries.")
                    if (parent.result or {}).get("company") != Catalog(agent_path).config["company"]:
                        raise ContractError("Follow-up cannot cross company boundaries.")
                    summary = str((parent.result or {}).get("summary", ""))[:12_000]
                    job.payload["parent_job_id"] = parent.job_id
                    job.payload["execution_task"] = (
                        "Previous completed task (context only):\n" + parent.payload["task"][:12_000]
                        + "\nPrevious result (verify current workspace before relying on it):\n" + summary
                        + "\n\nCurrent user task:\n" + task.strip()
                    )
                self._check_capacity()
                reserved = self._reserve_worker()
                try:
                    self._persist(job)
                    self.jobs[job_id] = job
                except Exception:
                    self._release_worker(reserved)
                    raise
                self._launch(job, reserved)
                return job

    def get(self, job_id: str) -> Job | None:
        if not isinstance(job_id, str) or not re.fullmatch(r"[0-9a-f]{32}", job_id):
            return None
        with self._lock:
            return self.jobs.get(job_id) or self._restore(self._job_file(job_id))

    def recent(self, limit: int = 50) -> list[Job]:
        with self._lock:
            return sorted(self.jobs.values(), key=lambda job: job.created_at, reverse=True)[:limit]

    def wait_for_workers(self, timeout: float) -> bool:
        """Wait a bounded time for already-dispatched workers to release files."""

        deadline = time.monotonic() + max(0.0, timeout)
        with self._lock:
            threads = [job.thread for job in self.jobs.values() if job.thread is not None]
        for thread in threads:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            thread.join(remaining)
        return all(not thread.is_alive() for thread in threads)

    def _check_capacity(self) -> None:
        if sum(job.status in {"queued", "running"} for job in self.jobs.values()) >= self.max_active:
            raise ContractError("All worker slots are busy. Wait for an active task to finish.")

    def _reserve_worker(self) -> bool:
        semaphore = self._worker_semaphore
        if semaphore is None:
            return False
        if not semaphore.acquire(blocking=False):
            raise ContractError("All tenant worker slots are busy. Wait for an active task to finish.")
        return True

    def _release_worker(self, reserved: bool) -> None:
        if reserved and self._worker_semaphore is not None:
            self._worker_semaphore.release()

    def _run_reserved(self, job: Job, reserved: bool) -> None:
        try:
            self._run(job)
        finally:
            self._release_worker(reserved)

    def _launch(self, job: Job, reserved: bool) -> None:
        job.thread = threading.Thread(target=self._run_reserved, args=(job, reserved), daemon=True)
        try:
            job.thread.start()
        except Exception:
            self._release_worker(reserved)
            raise

    def snapshot(self, job: Job) -> dict[str, Any]:
        with self._lock:
            value = copy.deepcopy(job.public())
            payload = dict(job.payload)
        run_id = payload.get("run_id", "")
        if value["status"] in {"running", "blocked", "error", "awaiting_approval"} and re.fullmatch(r"[0-9a-f]{32}", run_id):
            try:
                path = self._agent_path(payload["agent"]) / ".runs" / run_id / "state.json"
                value["result"] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, ContractError):
                pass
        if self.public_mode:
            value["result"] = self._public_result(value.get("result"), payload)
            value["error"] = self._public_redact(value.get("error", ""), payload)
        return value

    def _public_redact(self, value: Any, payload: dict[str, Any]) -> Any:
        """Remove host path identities recursively from a public response value."""
        replacements: list[tuple[re.Pattern[str], str, int]] = []

        def add_path(path: Path, replacement: str) -> None:
            private = str(path)
            normalized = private.replace("\\", "/")
            pattern = re.escape(normalized).replace("/", r"[\\/]")
            flags = re.IGNORECASE if os.name == "nt" else 0
            replacements.append((re.compile(pattern, flags), replacement, len(private)))

        try:
            add_path(self._agent_path(payload.get("agent", "")), str(payload.get("agent", "")))
        except (ContractError, OSError, ValueError):
            pass
        try:
            add_path(self._workspace_path(payload.get("workspace", "")), str(payload.get("workspace", "")))
        except (ContractError, OSError, ValueError):
            pass
        if self.workspace_root is not None:
            add_path(self.workspace_root.parent, "<private-user-root>")
        for root in self.agent_roots:
            add_path(root, "<private-agent-root>")
        replacements.sort(key=lambda item: item[2], reverse=True)

        def redact(item: Any) -> Any:
            if isinstance(item, str):
                for pattern, public, _length in replacements:
                    item = pattern.sub(lambda _match, replacement=public: replacement, item)
                return item
            if isinstance(item, list):
                return [redact(child) for child in item]
            if isinstance(item, dict):
                return {str(key): redact(child) for key, child in item.items()}
            return item

        return redact(value)

    def _public_result(self, result: Any, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(result, dict):
            return None
        allowed = {
            key: copy.deepcopy(result[key])
            for key in (
                "version", "run_id", "agent", "company", "backend", "status", "summary",
                "history", "steps", "failures", "elapsed_seconds", "dirty", "reviewed",
                "require_approvals",
            )
            if key in result
        }
        allowed["workspace"] = str(payload.get("workspace", ""))
        in_flight = result.get("in_flight")
        if isinstance(in_flight, dict):
            allowed["in_flight"] = {
                key: copy.deepcopy(in_flight[key])
                for key in ("kind", "step", "decision")
                if key in in_flight
            }
        else:
            allowed["in_flight"] = None
        pending = result.get("pending_approval")
        if isinstance(pending, dict):
            allowed["pending_approval"] = {
                key: copy.deepcopy(pending[key])
                for key in ("id", "tool", "arguments", "action_sha256")
                if key in pending
            }
        else:
            allowed["pending_approval"] = None
        approvals = result.get("approvals")
        if isinstance(approvals, list):
            allowed["approvals"] = [
                {
                    key: copy.deepcopy(record[key])
                    for key in ("id", "tool", "arguments", "decision", "at")
                    if isinstance(record, dict) and key in record
                }
                for record in approvals
                if isinstance(record, dict)
            ]
        return self._public_redact(allowed, payload)

    def configuration(self) -> dict[str, Any]:
        readiness = {} if self.public_mode else codex_readiness()
        provider = self.provider_status()
        profiles = read_json(LIBRARY / "profiles.json")
        codex_available = ("codex" in self.allowed_backends and bool(readiness.get("installed"))
                           and bool(readiness.get("credentials_present"))
                           and readiness.get("sandbox_configured", True))
        default_workspace = (
            "default"
            if self.public_mode
            else str(self.default_workspace or (self.template_root / "workspace"))
        )
        backends = [
            {"id": "demo", "label": "Offline-Demo", "available": "demo" in self.allowed_backends, "tool_approvals": True, "detail": "Deterministischer Funktionstest mit optionaler Freigabe der Dateiänderungen, kein Sprachmodell."},
            {"id": "codex", "label": "Codex CLI", "available": codex_available,
             "readiness": readiness, "tool_approvals": True,
             "detail": "Lokale CLI und Zugangsdaten erkannt; Modellzugriff ist damit noch nicht bestätigt. Standard: gpt-5.6-luna mit niedrigem Reasoning und isolierter CLI-Konfiguration."
             if codex_available else ("Die konfigurierte Windows-Sandbox fehlt oder ist ungültig. Codex lokal einrichten; es wurde kein Modell aufgerufen."
                                     if not readiness.get("sandbox_configured", True)
                                     else "Lokale Codex-CLI oder Zugangsdaten fehlen. Erst installieren und anmelden."),
             "approval_detail": "Freigabemodus: Codex liefert read-only Vorschläge; ein allowlist-basierter Host-Executor führt freigegebene Aktionen aus. Die direkte Codex-CLI bietet keine per-tool interception."},
            {"id": "deepseek", "label": "DeepSeek API", "available": "deepseek" in self.allowed_backends and provider["configured"], "tool_approvals": True, "readiness": provider, "detail": "API-Schlüssel in den Provider-Einstellungen einrichten. Modellzugriff ist erst durch einen erfolgreichen Auftrag bestätigt. Dateiänderungen und Tests benötigen eine konkrete Freigabe."},
        ]
        if self.public_mode:
            backends = [backend for backend in backends if backend["id"] in self.allowed_backends]
        elif "api" in self.allowed_backends:
            try:
                ApiBackend()
                api_available = True
            except (ContractError, ValueError):
                api_available = False
            backends.append({"id": "api", "label": "Eigene Modell-API", "available": api_available,
                             "tool_approvals": True,
                             "detail": "Anbieterunabhaengige Chat-Completions-API. Servervariablen AGENTKIT_API_BASE_URL, AGENTKIT_API_KEY und AGENTKIT_API_MODEL einrichten. Modellzugriff ist erst nach einem erfolgreichen Auftrag bestaetigt."})
        if not self.public_mode and "anthropic" in self.allowed_backends:
            anthropic_status = self.anthropic_provider.status()
            backends.append({"id": "anthropic", "label": "Anthropic Claude", "available": anthropic_status["configured"],
                             "tool_approvals": True, "readiness": anthropic_status,
                             "detail": "Native Anthropic Messages API. Standard: Claude Haiku 4.5. Schluessel lokal geschuetzt; Schreib- und Testaktionen benoetigen Freigaben."})
        if not self.public_mode and "ollama" in self.allowed_backends:
            try:
                OllamaBackend()
                ollama_available = True
            except (ContractError, ValueError):
                ollama_available = False
            backends.append({"id": "ollama", "label": "Lokale KI · Ollama", "available": ollama_available,
                             "tool_approvals": True,
                             "detail": "Privater Ollama-Modellserver. Standard: Qwen3 Coder Next. Kein Cloud-Fallback. HTTP im lokalen Netz ist unverschluesselt; Schreib- und Testaktionen benoetigen Freigaben."})
        return {
            "profiles": list(profiles),
            "profile_catalog": [
                {
                    "id": profile_id,
                    "description": profile["description"],
                    "roles": profile["roles"],
                    "require_review": profile["require_review"],
                }
                for profile_id, profile in profiles.items()
            ],
            "default_workspace": default_workspace,
            "public_multiuser": self.public_mode,
            "preferred_agent": "" if self.public_mode else self.preferred_agent,
            "preferred_backend": "" if self.public_mode else self.preferred_backend,
            "starter_task": "" if self.public_mode else self.starter_task,
            "backends": backends,
        }

    def provider_status(self) -> dict[str, Any]:
        if self.public_mode:
            return {
                "configured": bool(self._provider_api_key),
                "source": "managed" if self._provider_api_key else "none",
                "storage_available": False,
            }
        try:
            return self.providers.status()
        except (ContractError, OSError, ValueError):
            return {"configured": False, "source": "none", "storage_available": os.name == "nt",
                    "error": "Gespeicherter Provider-Schlüssel kann nicht gelesen werden. Bitte ersetzen oder entfernen."}

    def artifact(self, job_id: str, relative: str) -> bytes:
        job = self.get(job_id)
        if job is None:
            raise ContractError("Job not found.")
        snapshot = self.snapshot(job)
        allowed = {
            name for record in (snapshot.get("result") or {}).get("history", [])
            for name in record.get("report", {}).get("artifacts", [])
        }
        if relative not in allowed:
            raise ContractError("Artifact was not reported by this task.")
        workspace = self._workspace_path(job.payload["workspace"])
        try:
            path = safe_workspace_path(workspace, relative)
            with path.open("rb") as handle:
                data = handle.read(2_000_001)
        except FileNotFoundError as exc:
            raise ContractError("Artifact no longer exists.") from exc
        except (PermissionError, ContractError) as exc:
            denied = isinstance(exc, PermissionError) or isinstance(exc.__cause__, PermissionError)
            if not denied:
                raise
            if job.payload.get("backend") != "codex":
                raise ContractError("Artifact cannot be read.") from exc
            data = read_codex_artifact(workspace, relative)
        if len(data) > 2_000_000:
            raise ContractError("Artifact exceeds the 2 MB download limit; open it in the workspace.")
        return data

    def resume(self, job_id: str, feedback: str, acknowledge_interruption: bool) -> Job:
        if not isinstance(feedback, str) or not feedback.strip():
            raise ContractError("Feedback is required when resuming a job.")
        if len(feedback) > 20_000 or not isinstance(acknowledge_interruption, bool):
            raise ContractError("Invalid feedback or interruption acknowledgment.")
        with self._lock:
            job = self.jobs.get(job_id)
            if job is None:
                raise ContractError("Job not found.")
            if job.status in {"queued", "running"} or (job.thread and job.thread.is_alive()):
                raise ContractError("Job is already running.")
            if job.status not in {"blocked", "error"}:
                raise ContractError("Only blocked or failed jobs can be resumed.")
            self._check_capacity()
            if not job.payload.get("run_id"):
                raise ContractError("Legacy job has no recovery checkpoint identity; inspect its workspace before starting a new task.")
            checkpoint = self._agent_path(job.payload["agent"]) / ".runs" / job.payload["run_id"] / "state.json"
            if not checkpoint.is_file() and not acknowledge_interruption:
                raise ContractError("Missing checkpoint: inspect the workspace and acknowledge the unknown outcome before continuing.")
            reserved = self._reserve_worker()
            job.payload["feedback"] = feedback.strip()
            job.payload.pop("approval_id", None)
            job.payload.pop("approval_decision", None)
            job.payload["acknowledge_interruption"] = bool(acknowledge_interruption)
            job.error = ""
            job.status = "queued"
            try:
                self._persist(job)
            except Exception:
                self._release_worker(reserved)
                raise
            self._launch(job, reserved)
        return job

    def approval(self, job_id: str, approval_id: str, decision: str) -> Job:
        if not isinstance(approval_id, str) or not re.fullmatch(r"[0-9a-f]{32}", approval_id):
            raise ContractError("Invalid approval identity.")
        if decision not in ("approve", "reject"):
            raise ContractError("Approval decision must be approve or reject.")
        job = self.get(job_id)
        if job is None:
            raise ContractError("Job not found.")
        with self._lock:
            submitted = job.payload.get("approval_submissions", {})
            if job.status in {"queued", "running"} or (job.thread and job.thread.is_alive()):
                if submitted.get(approval_id) == decision:
                    return job
                raise ContractError("Job is already running.")
            run_id = job.payload.get("run_id", "")
            if not re.fullmatch(r"[0-9a-f]{32}", run_id):
                raise ContractError("Job has no valid checkpoint identity.")
            checkpoint = self._agent_path(job.payload["agent"]) / ".runs" / run_id / "state.json"
            state = read_json(checkpoint)
            pending = state.get("pending_approval") or {}
            if state.get("status") != "awaiting_approval" or pending.get("id") != approval_id or state.get("in_flight"):
                if approval_id in submitted:
                    if submitted[approval_id] != decision:
                        raise ContractError("This approval already has a different decision.")
                    return job
                raise ContractError("Approval is stale or the action outcome requires investigation.")
            self._check_capacity()
            reserved = self._reserve_worker()
            job.payload.setdefault("approval_submissions", {})[approval_id] = decision
            job.payload.update(approval_id=approval_id, approval_decision=decision)
            job.error = ""
            job.status = "queued"
            try:
                self._persist(job)
            except Exception:
                self._release_worker(reserved)
                raise
            self._launch(job, reserved)
        return job


INDEX = (Path(__file__).parent / "index.html").read_bytes()


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def make_handler(manager: JobManager | None, *, runtime_resolver=None):
    if manager is None and runtime_resolver is None:
        raise ValueError("A manager or public runtime resolver is required.")
    local_conversations = Conversations(manager) if manager is not None else None

    class Handler(BaseHTTPRequestHandler):
        server_version = "AgentKitCockpit/0.1"

        def _send(self, status: int, value: Any, content_type: str = "application/json", *, download: bool = False, filename: str = ""):
            body = value if isinstance(value, bytes) else json_bytes(value)
            script_sources = "'none'"
            if content_type == "text/html":
                script_sources = " ".join(
                    "'sha256-" + base64.b64encode(hashlib.sha256(
                        script.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                    ).digest()).decode("ascii") + "'"
                    for script in re.findall(rb"<script>(.*?)</script>", body, flags=re.DOTALL)
                ) or "'none'"
            self.send_response(status)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            if download:
                disposition = "attachment" + ("; filename*=UTF-8''" + quote(filename, safe="") if filename else "")
                self.send_header("Content-Disposition", disposition)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", f"default-src 'self'; script-src {script_sources}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            for name, header_value in getattr(self, "_extra_response_headers", {}).items():
                if name.lower() not in {
                    "content-type", "content-length", "content-security-policy", "cache-control",
                    "x-content-type-options", "x-frame-options", "referrer-policy",
                }:
                    self.send_header(name, header_value)
            if not getattr(self, "_response_recorded", False):
                callback = getattr(self, "_response_callback", None)
                if callback is not None:
                    callback(int(status))
                self._response_recorded = True
            try:
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                # Browser navigation can cancel an in-flight local response.
                return

        def _body(self, maximum: int = 64_000) -> dict[str, Any]:
            if self.headers.get("Transfer-Encoding"):
                raise ContractError("Transfer encoding is not supported.")
            if self.headers.get_content_type() != "application/json":
                raise ContractError("Content-Type must be application/json.")
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > maximum:
                raise ContractError("Request body is too large.")
            self.connection.settimeout(10)
            raw = self.rfile.read(length)
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise ContractError("Request body must be a JSON object.")
            return value

        def _local_request(self) -> bool:
            authority = self.headers.get("Host", "")
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            origin = self.headers.get("Origin")
            if authority not in allowed or (origin and origin != f"http://{authority}") or self.headers.get("Sec-Fetch-Site") == "cross-site":
                self._send(HTTPStatus.FORBIDDEN, {"error": "Only same-origin local requests are allowed."})
                return False
            return True

        def _prepare_request(self) -> bool:
            # BaseHTTPRequestHandler may reuse one handler for a keep-alive
            # connection. Response audit state is request-scoped.
            self._response_recorded = False
            self._response_callback = None
            if runtime_resolver is None:
                if not self._local_request():
                    return False
                self._active_manager = manager
                self._active_conversations = local_conversations
                return True
            runtime = runtime_resolver(self)
            if runtime is None:
                return False
            self._active_manager = runtime.manager
            self._active_conversations = runtime.conversations
            self._active_runtime = runtime
            self._request_context = getattr(runtime, "context", None)
            self._extra_response_headers = dict(getattr(runtime, "response_headers", {}))
            self._response_callback = getattr(runtime, "response_callback", None)
            return True

        def do_GET(self):  # noqa: N802
            if not self._prepare_request():
                return
            manager = self._active_manager
            conversations = self._active_conversations
            parsed = urlparse(self.path)
            if parsed.path == "/favicon.ico":
                self._send(HTTPStatus.NO_CONTENT, b"", "image/x-icon")
                return
            if parsed.path == "/settings":
                self._send(HTTPStatus.OK, (Path(__file__).parent / "settings.html").read_bytes(), "text/html")
                return
            if parsed.path == "/assistants":
                self._send(HTTPStatus.OK, (Path(__file__).parent / "assistants.html").read_bytes(), "text/html")
                return
            if parsed.path in {"/api/providers/deepseek", "/api/providers/anthropic"}:
                status = manager.provider_status() if parsed.path.endswith("deepseek") else manager.anthropic_provider.status()
                self._send(HTTPStatus.OK, status)
                return
            if parsed.path == "/api/agents/instructions":
                try:
                    agent = parse_qs(parsed.query).get("agent", [""])[0]
                    self._send(HTTPStatus.OK, manager.get_instructions(agent))
                except (ContractError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            attachment_match = re.fullmatch(r"/api/conversations/([0-9a-f]{32})/attachments/([0-9a-f]{32})", parsed.path)
            if attachment_match:
                try:
                    data, filename = conversations.download(attachment_match[1], attachment_match[2])
                except (ContractError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return
                self._send(HTTPStatus.OK, data, "application/octet-stream", download=True, filename=filename)
                return
            if parsed.path == "/chat":
                self._send(HTTPStatus.OK, (Path(__file__).parent / "chat.html").read_bytes(), "text/html")
                return
            if parsed.path == "/api/conversations":
                self._send(HTTPStatus.OK, {"conversations": conversations.recent()})
                return
            match = re.fullmatch(r"/api/conversations/([0-9a-f]{32})", parsed.path)
            if match:
                try:
                    value = conversations.get(match[1])
                except (ContractError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return
                self._send(HTTPStatus.OK, value)
                return
            if parsed.path == "/" or parsed.path == "/index.html":
                self._send(HTTPStatus.OK, INDEX, "text/html")
                return
            if parsed.path == "/api/health":
                self._send(HTTPStatus.OK, {"status": "ok", "local_only": True})
                return
            if parsed.path == "/api/session":
                self._send(HTTPStatus.OK, {
                    "authenticated": True,
                    "public_multiuser": False,
                    "csrf_token": "local-loopback",
                })
                return
            if parsed.path == "/api/config":
                self._send(HTTPStatus.OK, manager.configuration())
                return
            if parsed.path == "/api/agents":
                try:
                    include_archived = parse_qs(parsed.query).get("include_archived", ["false"])[0].lower() == "true"
                    self._send(HTTPStatus.OK, {"agents": manager.agents(include_archived=include_archived)})
                except (ContractError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            if parsed.path == "/api/jobs":
                self._send(HTTPStatus.OK, {"jobs": [manager.snapshot(job) for job in manager.recent()]})
                return
            if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/artifacts"):
                try:
                    relative = parse_qs(parsed.query).get("path", [""])[0]
                    data = manager.artifact(unquote(parsed.path.split("/")[3]), relative)
                except (ContractError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return
                self._send(HTTPStatus.OK, data, "application/octet-stream", download=True)
                return
            if parsed.path.startswith("/api/jobs/"):
                job = manager.get(unquote(parsed.path.rsplit("/", 1)[-1]))
                if job is None:
                    self._send(HTTPStatus.NOT_FOUND, {"error": "job_not_found"})
                else:
                    self._send(HTTPStatus.OK, manager.snapshot(job))
                return
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self):  # noqa: N802
            if not self._prepare_request():
                return
            manager = self._active_manager
            conversations = self._active_conversations
            path = urlparse(self.path).path
            if path == "/api/agents/instructions":
                try:
                    value = manager.update_instructions(self._body(200_000))
                except InstructionConflict as exc:
                    self._send(HTTPStatus.CONFLICT, {"error": str(exc)})
                    return
                except (ContractError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return
                self._send(HTTPStatus.OK, value)
                return
            if path == "/api/connectors/github/preview":
                try:
                    preview = preview_file(self._body())
                except (ContractError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return
                self._send(HTTPStatus.OK, preview)
                return
            if path in {"/api/providers/deepseek", "/api/providers/anthropic"}:
                try:
                    settings = manager.providers if path.endswith("deepseek") else manager.anthropic_provider
                    body = self._body()
                    if body.get("action") == "save" and set(body) == {"action", "api_key"}:
                        settings.save(body["api_key"])
                    elif body == {"action": "clear"}:
                        settings.clear()
                    else:
                        raise ContractError("Invalid provider operation.")
                except (ContractError, OSError, ValueError):
                    self._send(HTTPStatus.BAD_REQUEST, {"error": "Provider-Einstellung konnte nicht gespeichert werden. Schlüssel und lokale Speicherberechtigung prüfen."})
                    return
                self._send(HTTPStatus.OK, manager.provider_status() if path.endswith("deepseek") else settings.status())
                return
            attachment_match = re.fullmatch(r"/api/conversations/([0-9a-f]{32})/attachments", path)
            if attachment_match:
                try:
                    metadata = conversations.upload(attachment_match[1], self._body(2_810_000))
                except (ContractError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return
                self._send(HTTPStatus.CREATED, metadata)
                return
            approval_match = re.fullmatch(r"/api/jobs/([0-9a-f]{32})/approval", path)
            if approval_match:
                try:
                    body = self._body()
                    job = manager.approval(approval_match[1], body.get("approval_id", ""), body.get("decision", ""))
                except (ContractError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return
                self._send(HTTPStatus.ACCEPTED, manager.snapshot(job))
                return
            match = re.fullmatch(r"/api/conversations/([0-9a-f]{32})/messages", path)
            if path == "/api/conversations" or match:
                try:
                    value = conversations.send(match[1], self._body()) if match else conversations.create(self._body())
                except (ContractError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                    return
                self._send(HTTPStatus.ACCEPTED if match else HTTPStatus.CREATED, value)
                return
            if path == "/api/agents/archive":
                try:
                    body = self._body()
                    agent = manager.archive_agent(body)
                except (ContractError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": f"{type(exc).__name__}: {exc}"})
                    return
                self._send(HTTPStatus.OK, agent)
                return
            if path == "/api/agents":
                try:
                    agent = manager.create_agent(self._body())
                except (ContractError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": f"{type(exc).__name__}: {exc}"})
                    return
                self._send(HTTPStatus.CREATED, agent)
                return
            if path.startswith("/api/jobs/") and path.endswith("/resume"):
                job_id = unquote(path.split("/")[3])
                try:
                    body = self._body()
                    job = manager.resume(
                        job_id,
                        body.get("feedback", ""),
                        body.get("acknowledge_interruption", False),
                    )
                except (ContractError, json.JSONDecodeError, OSError, ValueError) as exc:
                    self._send(HTTPStatus.BAD_REQUEST, {"error": f"{type(exc).__name__}: {exc}"})
                    return
                self._send(HTTPStatus.ACCEPTED, manager.snapshot(job))
                return
            if path != "/api/jobs":
                self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            try:
                job = manager.start(self._body())
            except (ContractError, json.JSONDecodeError, OSError, ValueError) as exc:
                self._send(HTTPStatus.BAD_REQUEST, {"error": f"{type(exc).__name__}: {exc}"})
                return
            self._send(HTTPStatus.ACCEPTED, manager.snapshot(job))

        def log_message(self, format: str, *args):
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local AgentKit Cockpit")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--default-workspace", type=Path)
    parser.add_argument("--preferred-agent", default="")
    parser.add_argument("--preferred-backend", choices=("demo", "codex", "deepseek", "api", "anthropic", "ollama"), default="")
    parser.add_argument("--starter-task", default="")
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        parser.error("This single-owner server only supports loopback: --host 127.0.0.1")
    state_dir = TEMPLATE_ROOT / "cockpit" / ".runs"
    state_dir.mkdir(parents=True, exist_ok=True)
    with lock(state_dir / ".server.lock"):
        manager = JobManager(
            default_workspace=args.default_workspace,
            preferred_agent=args.preferred_agent,
            preferred_backend=args.preferred_backend,
            starter_task=args.starter_task,
        )
        server = ThreadingHTTPServer((args.host, args.port), make_handler(manager))
        url = f"http://{args.host}:{args.port}"
        print(f"AI Studio: {url}", flush=True)
        if args.open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return 0
        finally:
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
