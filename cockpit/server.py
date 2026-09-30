"""Small local web cockpit for the AgentKit engine."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import copy
import sys
import threading
import tempfile
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse, parse_qs, quote

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEMPLATE_ROOT))

from agentkit.backends import CodexBackend, DeepSeekBackend, DemoBackend, codex_readiness  # noqa: E402
from agentkit.approvals import safe_workspace_path  # noqa: E402
from agentkit.catalog import Catalog  # noqa: E402
from agentkit.codex_artifacts import read_codex_artifact  # noqa: E402
from agentkit.contracts import ContractError  # noqa: E402
from agentkit.engine import Engine  # noqa: E402
from agentkit.scaffold import create  # noqa: E402
from agentkit.contracts import LIBRARY, read_json  # noqa: E402
from agentkit.storage import lock  # noqa: E402
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
    def __init__(self, template_root: Path = TEMPLATE_ROOT, state_dir: Path | None = None, max_active: int = 4):
        self.template_root = template_root.resolve()
        self.agent_roots = (
            self.template_root / "agents",
            self.template_root / "generated",
        )
        self.state_dir = (state_dir or self.template_root / "cockpit" / ".runs").resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.providers = ProviderSettings(self.state_dir)
        self.assistant_settings = AssistantSettings(self.state_dir)
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
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = self.template_root / candidate
        candidate = candidate.resolve()
        if not any(candidate.is_relative_to(root.resolve()) for root in self.agent_roots):
            raise ContractError("Agent must be inside agents/ or generated/.")
        if not (candidate / "agent.json").is_file():
            raise ContractError("Agent pack is missing agent.json.")
        return candidate

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

    @staticmethod
    def _instruction_result(agent: Path, document) -> dict[str, Any]:
        config = Catalog(agent).config
        return {"agent": str(agent), "id": config["id"], "text": document.text, "revision": document.revision}

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
                    payload_path = Path(payload["agent"]).expanduser()
                    if not payload_path.is_absolute():
                        payload_path = self.template_root / payload_path
                    payload_agent = str(payload_path.resolve())
                except OSError as exc:
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
                    path, replace_document(path, payload["text"], payload["revision"])
                )

    @staticmethod
    def _workspace_path(value: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ContractError("Workspace is required.")
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
                        "path": str(agent_json.parent),
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
            target = create(self.template_root / "generated" / name, profile, name, company)
            if instructions.strip():
                soul = target / "SOUL.md"
                with lock(target / ".instructions.lock"):
                    with soul.open("a", encoding="utf-8") as handle:
                        handle.write("\n\n## Owner instructions\n\n" + instructions.strip() + "\n")
        return next(agent for agent in self.agents(include_archived=True) if agent["path"] == str(target))

    def archive_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or set(payload) != {"agent", "archived"}:
            raise ContractError("Archive request must contain agent and archived.")
        if not isinstance(payload["agent"], str) or not isinstance(payload["archived"], bool):
            raise ContractError("agent must be text and archived must be boolean.")
        agent = self._agent_path(payload["agent"])
        registered = next((item for item in self.agents(include_archived=True)
                           if Path(item["path"]).resolve() == agent), None)
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
            model = job.payload.get("model") or None
            backend_type = {
                "demo": DemoBackend,
                "codex": CodexBackend,
                "deepseek": DeepSeekBackend,
            }.get(backend_name)
            if backend_type is None:
                raise ContractError(f"Unknown backend: {backend_name}")
            if backend_name == "deepseek":
                key = self.providers.api_key()
                if not key:
                    raise ContractError("DeepSeek ist nicht eingerichtet. Bitte Provider-Einstellungen öffnen.")
                backend = DeepSeekBackend(model, api_key=key, base_url="https://api.deepseek.com")
            else:
                backend = DemoBackend() if backend_name == "demo" else backend_type(model)
            run_id = job.payload["run_id"]
            if not re.fullmatch(r"[0-9a-f]{32}", run_id):
                raise ContractError("Invalid run identity.")
            checkpoint = agent_path / ".runs" / run_id
            run_dir = checkpoint if (checkpoint / "state.json").is_file() else None
            result = Engine(agent_path, workspace, backend,
                            require_approvals=backend_name in {"codex", "deepseek"} or job.payload.get("require_approvals", False),
                            core_snapshot=job.payload.get("core_snapshot")).run(
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
        require_approvals = backend_name in {"codex", "deepseek"} or payload.get("require_approvals", False)
        if backend_name not in {"demo", "codex", "deepseek"}:
            raise ContractError("Unknown backend.")
        if len(payload.get("model", "")) > 200:
            raise ContractError("Model name is too large.")
        task = payload.get("task")
        if not isinstance(task, str) or not task.strip():
            raise ContractError("Task must not be empty.")
        if len(task) > 20_000:
            raise ContractError("Task is too large.")
        agent_path = self._agent_path(str(payload.get("agent", "")))
        self._workspace_path(str(payload.get("workspace", "")))
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
                    "agent": str(agent_path), "workspace": str(Path(payload["workspace"]).expanduser().resolve()),
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
                        "agent": str(agent_path),
                        "run_id": uuid.uuid4().hex,
                        "backend": str(payload.get("backend", "demo")),
                        "model": str(payload.get("model", "")),
                        "workspace": str(Path(payload["workspace"]).expanduser().resolve()),
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
                self._persist(job)
                self.jobs[job_id] = job
                job.thread = threading.Thread(target=self._run, args=(job,), daemon=True)
                job.thread.start()
                return job

    def get(self, job_id: str) -> Job | None:
        if not isinstance(job_id, str) or not re.fullmatch(r"[0-9a-f]{32}", job_id):
            return None
        with self._lock:
            return self.jobs.get(job_id) or self._restore(self._job_file(job_id))

    def recent(self, limit: int = 50) -> list[Job]:
        with self._lock:
            return sorted(self.jobs.values(), key=lambda job: job.created_at, reverse=True)[:limit]

    def _check_capacity(self) -> None:
        if sum(job.status in {"queued", "running"} for job in self.jobs.values()) >= self.max_active:
            raise ContractError("All worker slots are busy. Wait for an active task to finish.")

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
        return value

    def configuration(self) -> dict[str, Any]:
        readiness = codex_readiness()
        provider = self.provider_status()
        codex_available = (readiness["installed"] and readiness["credentials_present"]
                           and readiness.get("sandbox_configured", True))
        return {"profiles": list(read_json(LIBRARY / "profiles.json")), "default_workspace": str(self.template_root / "workspace"), "backends": [
            {"id": "demo", "label": "Offline-Demo", "available": True, "tool_approvals": True, "detail": "Deterministischer Funktionstest mit optionaler Freigabe der Dateiänderungen, kein Sprachmodell."},
            {"id": "codex", "label": "Codex CLI", "available": codex_available,
             "readiness": readiness, "tool_approvals": True,
             "detail": "Lokale CLI und Zugangsdaten erkannt; Modellzugriff ist damit noch nicht bestätigt. Standard: gpt-5.6-luna mit niedrigem Reasoning und isolierter CLI-Konfiguration."
             if codex_available else ("Die konfigurierte Windows-Sandbox fehlt oder ist ungültig. Codex lokal einrichten; es wurde kein Modell aufgerufen."
                                     if not readiness.get("sandbox_configured", True)
                                     else "Lokale Codex-CLI oder Zugangsdaten fehlen. Erst installieren und anmelden."),
             "approval_detail": "Freigabemodus: Codex liefert read-only Vorschläge; ein allowlist-basierter Host-Executor führt freigegebene Aktionen aus. Die direkte Codex-CLI bietet keine per-tool interception."},
            {"id": "deepseek", "label": "DeepSeek API", "available": provider["configured"], "tool_approvals": True, "readiness": provider, "detail": "API-Schlüssel in den Provider-Einstellungen einrichten. Modellzugriff ist erst durch einen erfolgreichen Auftrag bestätigt. Dateiänderungen und Tests benötigen eine konkrete Freigabe."},
        ]}

    def provider_status(self) -> dict[str, Any]:
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
        path = safe_workspace_path(Path(job.payload["workspace"]), relative)
        try:
            with path.open("rb") as handle:
                data = handle.read(2_000_001)
        except FileNotFoundError as exc:
            raise ContractError("Artifact no longer exists.") from exc
        except PermissionError as exc:
            if job.payload.get("backend") != "codex":
                raise ContractError("Artifact cannot be read.") from exc
            data = read_codex_artifact(Path(job.payload["workspace"]), relative)
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
            job.payload["feedback"] = feedback.strip()
            job.payload.pop("approval_id", None)
            job.payload.pop("approval_decision", None)
            job.payload["acknowledge_interruption"] = bool(acknowledge_interruption)
            job.error = ""
            job.status = "queued"
            self._persist(job)
            job.thread = threading.Thread(target=self._run, args=(job,), daemon=True)
            job.thread.start()
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
            job.payload.setdefault("approval_submissions", {})[approval_id] = decision
            job.payload.update(approval_id=approval_id, approval_decision=decision)
            job.error = ""
            job.status = "queued"
            self._persist(job)
            job.thread = threading.Thread(target=self._run, args=(job,), daemon=True)
            job.thread.start()
        return job


INDEX = (Path(__file__).parent / "index.html").read_bytes()


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def make_handler(manager: JobManager):
    conversations = Conversations(manager)

    class Handler(BaseHTTPRequestHandler):
        server_version = "AgentKitCockpit/0.1"

        def _send(self, status: int, value: Any, content_type: str = "application/json", *, download: bool = False, filename: str = ""):
            body = value if isinstance(value, bytes) else json_bytes(value)
            script_sources = "'none'"
            if content_type == "text/html":
                script_sources = " ".join(
                    "'sha256-" + base64.b64encode(hashlib.sha256(script).digest()).decode("ascii") + "'"
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
            self.send_header("Content-Security-Policy", f"default-src 'self'; script-src {script_sources}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

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

        def do_GET(self):  # noqa: N802
            if not self._local_request():
                return
            parsed = urlparse(self.path)
            if parsed.path == "/settings":
                self._send(HTTPStatus.OK, (Path(__file__).parent / "settings.html").read_bytes(), "text/html")
                return
            if parsed.path == "/assistants":
                self._send(HTTPStatus.OK, (Path(__file__).parent / "assistants.html").read_bytes(), "text/html")
                return
            if parsed.path == "/api/providers/deepseek":
                self._send(HTTPStatus.OK, manager.provider_status())
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
            if not self._local_request():
                return
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
            if path == "/api/providers/deepseek":
                try:
                    body = self._body()
                    if body.get("action") == "save" and set(body) == {"action", "api_key"}:
                        manager.providers.save(body["api_key"])
                    elif body == {"action": "clear"}:
                        manager.providers.clear()
                    else:
                        raise ContractError("Invalid provider operation.")
                except (ContractError, OSError, ValueError):
                    self._send(HTTPStatus.BAD_REQUEST, {"error": "Provider-Einstellung konnte nicht gespeichert werden. Schlüssel und lokale Speicherberechtigung prüfen."})
                    return
                self._send(HTTPStatus.OK, manager.provider_status())
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
                self._send(HTTPStatus.ACCEPTED, job.public())
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
                self._send(HTTPStatus.ACCEPTED, job.public())
                return
            if path != "/api/jobs":
                self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            try:
                job = manager.start(self._body())
            except (ContractError, json.JSONDecodeError, OSError, ValueError) as exc:
                self._send(HTTPStatus.BAD_REQUEST, {"error": f"{type(exc).__name__}: {exc}"})
                return
            self._send(HTTPStatus.ACCEPTED, job.public())

        def log_message(self, format: str, *args):
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local AgentKit Cockpit")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        parser.error("This single-owner server only supports loopback: --host 127.0.0.1")
    state_dir = TEMPLATE_ROOT / "cockpit" / ".runs"
    state_dir.mkdir(parents=True, exist_ok=True)
    with lock(state_dir / ".server.lock"):
        manager = JobManager()
        server = ThreadingHTTPServer((args.host, args.port), make_handler(manager))
        print(f"AI Studio: http://{args.host}:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return 0
        finally:
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
