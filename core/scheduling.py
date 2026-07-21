"""Deterministic, cost-aware scheduling for reusable agent instances.

The scheduler never reads file contents into prompts. It only decides whether a
governed orchestrator run is warranted and supplies stable, auditable metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import fnmatch
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time
from typing import Any, Protocol


SCHEDULE_FILE = "project/schedule.json"
STATE_FILE = "state/scheduler-state.json"
MAX_CONSECUTIVE_FAILURES = 3
MAX_INPUT_FILES = 1_000
MAX_INPUT_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_INPUT_BYTES = 100 * 1024 * 1024
MAX_INPUT_SCAN_ENTRIES = 10_000
MAX_INPUT_PATTERNS = 100
MAX_INPUT_PATTERN_LENGTH = 512
MAX_REQUIRED_INPUT_GROUPS = 100


@dataclass(frozen=True, slots=True)
class ScheduledDecision:
    should_enqueue: bool
    reason: str
    request_id: str | None = None
    task_text: str | None = None


class ScheduledOrchestrator(Protocol):
    """Minimal scheduler-facing runner contract with durable request identity."""

    def run(self, task: str, *, tools: dict[str, Any], request_id: str | None) -> Any: ...


class AdaptiveScheduler:
    """Evaluate declarative schedule signals without incurring LLM costs."""

    def __init__(self, root: Path, agent_config: dict[str, Any] | None = None):
        self.root = Path(root).resolve()
        self.agent_config = agent_config or {}
        self.schedule_path = self.root / SCHEDULE_FILE
        self.config = self._load_schedule()
        self._owned_in_flight_request_id: str | None = None
        self._owned_in_flight_token: str | None = None
        configured_state = self.config.get("state_file", STATE_FILE) if self.config else STATE_FILE
        declared_state = self.root / str(configured_state)
        if declared_state.is_symlink():
            raise ValueError("Scheduler state file must not be a symlink")
        requested_state = _safe_instance_path(self.root, configured_state)
        if requested_state is None:
            raise ValueError("Scheduler state path must stay inside the instance")
        self.state_path = requested_state
        self._assert_safe_state_path()

    @property
    def enabled(self) -> bool:
        return self.config is not None

    @property
    def dispatch_lock_path(self) -> Path:
        return self.state_path.with_suffix(".dispatch.lock")

    def evaluate(self, *, now: datetime | None = None) -> ScheduledDecision:
        """Return an idempotent task decision; this method does not call an LLM."""
        if not self.config:
            return ScheduledDecision(False, "schedule_disabled")
        now = _as_utc(now)
        state = self._read_state()
        if self._recover_in_flight(state, now):
            return ScheduledDecision(False, "already_enqueued", request_id=state.get("in_flight_request_id"))
        if state.get("consecutive_failures", 0) >= self._max_failures:
            return ScheduledDecision(False, "frozen_after_failures")

        input_hashes = self._input_hashes()
        required_input_counts = self._required_input_counts()
        reasons: list[str] = []
        if required_input_counts is not None and any(
            count < minimum for _, count, minimum in required_input_counts
        ):
            reasons.append("missing_data")
        if input_hashes != state.get("input_hashes", {}):
            if "input_globs" in self.config and not state.get("input_hashes"):
                reasons.append("new_input")
            elif "input_globs" in self.config:
                reasons.append("changed_input")
            else:
                reasons.append("input_changed")
        approval_path = _safe_instance_path(
            self.root, self.config.get("approval_state_file", "state/approvals.json")
        )
        if approval_path and _has_open_approvals(approval_path):
            reasons.append("pending_approval")
        if state.get("last_result") == "failed":
            reasons.append("recovery")
        if self._review_due(state, now):
            reasons.append("periodic_review")
        if not reasons:
            return ScheduledDecision(False, "idle")

        # Missing required data is a governed stop condition, not work that can
        # be advanced by another signal. Keeping only that reason also makes its
        # request identity stable after the successful status/wait run.
        if "missing_data" in reasons:
            reasons = ["missing_data"]

        # The order makes the agent's task focused even if several signals occur.
        reason = next(name for name in ("missing_data", "new_input", "changed_input", "input_changed", "pending_approval", "recovery", "periodic_review") if name in reasons)
        metadata = self._local_metadata(input_hashes, reasons, now, state, required_input_counts)
        request_id = self._request_id(metadata)
        if state.get("last_enqueued_request_id") == request_id:
            return ScheduledDecision(False, "already_enqueued", request_id=request_id)
        return ScheduledDecision(True, reason, request_id, self._render_prompt(metadata))

    def mark_enqueued(self, decision: ScheduledDecision) -> None:
        """Persist the exact input snapshot before dispatch to prevent duplicates."""
        if not decision.should_enqueue or not decision.request_id:
            return
        state = self._read_state()
        state["last_enqueued_request_id"] = decision.request_id
        state["input_hashes"] = self._input_hashes()
        state["in_flight_request_id"] = decision.request_id
        timestamp = _as_utc(None).isoformat()
        owner_token = secrets.token_hex(32)
        state["in_flight_at"] = timestamp
        state["in_flight_heartbeat_at"] = timestamp
        state["in_flight_owner_token"] = owner_token
        self._owned_in_flight_request_id = decision.request_id
        self._owned_in_flight_token = owner_token
        self._write_state(state)

    def record_result(self, *, success: bool, now: datetime | None = None) -> bool:
        """Record only this scheduler's dispatch result.

        A late worker must never clear a replacement run. Manual result records
        remain supported when no dispatch is currently in flight.
        """
        lock_token = self._acquire_dispatch_lock_with_retry()
        if lock_token is None:
            return False
        try:
            state = self._read_state()
            owns_dispatch = bool(
                self._owned_in_flight_request_id or self._owned_in_flight_token
            )
            if (owns_dispatch and not self._owns_in_flight(state)) or (
                not owns_dispatch and state.get("in_flight_request_id")
            ):
                return False
            state["last_result"] = "success" if success else "failed"
            state["last_result_at"] = _as_utc(now).isoformat()
            state["consecutive_failures"] = (
                0 if success else state.get("consecutive_failures", 0) + 1
            )
            self._clear_in_flight(state)
            if success:
                state["last_review_at"] = state["last_result_at"]
            self._write_state(state)
            return True
        finally:
            self.release_dispatch_lock(lock_token)

    def renew_in_flight(self, *, now: datetime | None = None) -> bool:
        """Renew the owned run's lease using a request-and-owner CAS."""
        lock_token = self.acquire_dispatch_lock()
        if lock_token is None:
            return False
        try:
            state = self._read_state()
            if not self._owns_in_flight(state):
                return False
            state["in_flight_heartbeat_at"] = _as_utc(now).isoformat()
            self._write_state(state)
            return True
        finally:
            self.release_dispatch_lock(lock_token)

    def _load_schedule(self) -> dict[str, Any] | None:
        embedded = self.agent_config.get("adaptive_schedule")
        if isinstance(embedded, dict) and embedded.get("enabled") is True:
            return embedded
        if not self.schedule_path.exists():
            return None
        try:
            config = json.loads(self.schedule_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(config, dict) or not isinstance(config.get("prompt"), dict):
            return None
        paths = config.get("input_paths", [])
        if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
            return None
        return config

    @property
    def _max_failures(self) -> int:
        value = self.config.get("max_consecutive_failures", MAX_CONSECUTIVE_FAILURES)  # type: ignore[union-attr]
        return value if isinstance(value, int) and value > 0 else MAX_CONSECUTIVE_FAILURES

    def _input_hashes(self) -> dict[str, str]:
        """Hash a bounded, instance-contained input snapshot."""
        hashes: dict[str, str] = {}
        total_bytes = 0
        for relative, path in self._input_candidates():
            if len(hashes) >= MAX_INPUT_FILES:
                break
            try:
                size = path.stat().st_size
            except OSError:
                continue
            remaining = MAX_TOTAL_INPUT_BYTES - total_bytes
            if size < 0 or size > MAX_INPUT_FILE_BYTES or size > remaining:
                continue
            try:
                result = _sha256(
                    path, max_bytes=min(MAX_INPUT_FILE_BYTES, remaining)
                )
            except OSError:
                continue
            if result is None:
                continue
            digest, bytes_read = result
            hashes[relative] = digest
            total_bytes += bytes_read
        return hashes

    def _input_candidates(self) -> list[tuple[str, Path]]:
        """Return deterministic, de-duplicated candidates from a bounded scan."""
        root = self.root.resolve()
        configured_paths = self.config.get("input_paths", [])  # type: ignore[union-attr]
        configured_globs = self.config.get("input_globs", [])  # type: ignore[union-attr]
        paths = configured_paths if isinstance(configured_paths, list) else []
        patterns = [
            pattern
            for pattern in configured_globs[:MAX_INPUT_PATTERNS]
            if _is_safe_relative_glob(pattern)
        ] if isinstance(configured_globs, list) else []
        exact_files: dict[str, Path] = {}
        directories: list[Path] = []
        for relative in paths[:MAX_INPUT_PATTERNS]:
            if not isinstance(relative, str):
                continue
            try:
                candidate = (root / relative).resolve(strict=True)
            except (OSError, RuntimeError):
                continue
            if not _is_within(candidate, root):
                continue
            if candidate.is_file():
                exact_files[candidate.relative_to(root).as_posix()] = candidate
            elif candidate.is_dir():
                directories.append(candidate)

        selected = dict(exact_files)
        if directories or patterns:
            for relative, resolved in _bounded_instance_files(root):
                if any(_is_within(resolved, directory) for directory in directories) or any(
                    _matches_relative_glob(relative, pattern) for pattern in patterns
                ):
                    selected.setdefault(relative, resolved)

        # Hash a resolved target only once even if several in-instance symlinks
        # or overlapping declarations refer to it.
        candidates: list[tuple[str, Path]] = []
        seen_targets: set[Path] = set()
        for relative, resolved in sorted(selected.items()):
            if resolved in seen_targets:
                continue
            seen_targets.add(resolved)
            candidates.append((relative, resolved))
        return candidates

    def _required_input_counts(self) -> list[tuple[str, int, int]] | None:
        """Return only opaque counts for valid required-input groups.

        Malformed groups are ignored. A syntactically valid group whose globs
        are all unsafe is counted as empty, so a bad path declaration fails
        closed instead of silently bypassing a required-data check.
        """
        groups = self.config.get("required_input_groups")  # type: ignore[union-attr]
        if not isinstance(groups, list):
            return None
        counts: list[tuple[str, int, int]] = []
        inventory = _bounded_instance_files(self.root.resolve())
        remaining_patterns = MAX_INPUT_PATTERNS
        for index, group in enumerate(groups[:MAX_REQUIRED_INPUT_GROUPS], start=1):
            if not isinstance(group, dict):
                continue
            minimum = group.get("minimum")
            globs = group.get("globs")
            if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 0:
                continue
            if not isinstance(globs, list):
                continue
            group_id = _public_required_group_id(group.get("name"), index)
            safe_globs = [
                pattern
                for pattern in globs[:remaining_patterns]
                if _is_safe_relative_glob(pattern)
            ]
            remaining_patterns -= len(safe_globs)
            if not safe_globs:
                counts.append((group_id, 0, minimum))
                continue
            matched: set[Path] = set()
            for relative, resolved in inventory:
                if not any(
                    _matches_relative_glob(relative, pattern)
                    for pattern in safe_globs
                ):
                    continue
                try:
                    size = resolved.stat().st_size
                except OSError:
                    continue
                if 0 <= size <= MAX_INPUT_FILE_BYTES:
                    matched.add(resolved)
                if len(matched) >= MAX_INPUT_FILES:
                    break
            counts.append((group_id, min(len(matched), MAX_INPUT_FILES), minimum))
        if len(groups) > MAX_REQUIRED_INPUT_GROUPS:
            counts.append(("group_limit", 0, 1))
        return counts

    def _review_due(self, state: dict[str, Any], now: datetime) -> bool:
        last = state.get("last_review_at")
        if not last:
            return not state.get("input_hashes")
        try:
            elapsed = now - _as_utc(datetime.fromisoformat(last))
        except (TypeError, ValueError):
            return True
        hours = self.config.get("review_interval_hours", self.config.get("periodic_review_hours", 168))  # type: ignore[union-attr]
        hours = hours if isinstance(hours, int) and hours > 0 else 168
        return elapsed >= timedelta(hours=hours)

    def _local_metadata(
        self,
        input_hashes: dict[str, str],
        reasons: list[str],
        now: datetime,
        state: dict[str, Any],
        required_input_counts: list[tuple[str, int, int]] | None,
    ) -> dict[str, Any]:
        metadata = {
            "agent_name": self.agent_config.get("agent_name", "automation-agent"),
            "reasons": reasons,
            "input_hashes": input_hashes,
            "attempt": 1
            if reasons == ["missing_data"]
            else state.get("consecutive_failures", 0) + 1,
            "evaluated_at": now.date().isoformat(),
        }
        if required_input_counts is not None:
            metadata["required_input_counts"] = [
                count for _, count, _ in required_input_counts
            ]
            metadata["missing_required_groups"] = [
                {"id": group_id, "count": count, "minimum": minimum}
                for group_id, count, minimum in required_input_counts
                if count < minimum
            ]
        return metadata

    @staticmethod
    def _request_id(metadata: dict[str, Any]) -> str:
        stable = {key: value for key, value in metadata.items() if key != "evaluated_at"}
        encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "schedule-" + hashlib.sha256(encoded).hexdigest()[:20]

    def _render_prompt(self, metadata: dict[str, Any]) -> str:
        profile = self.config.get("prompt_profiles", {}).get(metadata["reasons"][0])  # type: ignore[union-attr]
        template = profile or self.config.get("prompt", {}).get("template", "Pruefe {agent_name}: {reasons}.")  # type: ignore[union-attr]
        if not isinstance(template, str):
            template = "Pruefe {agent_name}: {reasons}."
        signal = json.dumps({
            "event_id": self._request_id(metadata),
            "input_count": len(metadata["input_hashes"]),
            "missing_required_groups": metadata.get("missing_required_groups", []),
            "reason": metadata["reasons"][0],
            "reasons": metadata["reasons"],
            "required_input_counts": metadata.get("required_input_counts", []),
        }, sort_keys=True, ensure_ascii=False)
        signal_line = "SCHEDULER_SIGNAL: " + signal
        values = {
            "agent_name": metadata["agent_name"],
            "reasons": ", ".join(metadata["reasons"]),
            "metadata_json": signal_line,
        }
        try:
            rendered = template.format(**values)
        except (KeyError, ValueError):
            rendered = "Pruefe geplante Signale. Metadaten: " + signal_line
        if signal_line not in rendered:
            rendered = f"{rendered}\n{signal_line}"
        return rendered

    @property
    def _in_flight_lease(self) -> timedelta:
        minutes = self.config.get("in_flight_lease_minutes", 15)  # type: ignore[union-attr]
        minutes = minutes if isinstance(minutes, int) and not isinstance(minutes, bool) and minutes > 0 else 15
        return timedelta(minutes=minutes)

    @property
    def _heartbeat_interval_seconds(self) -> float:
        return max(1.0, min(60.0, self._in_flight_lease.total_seconds() / 3))

    def _owns_in_flight(self, state: dict[str, Any]) -> bool:
        return bool(
            self._owned_in_flight_request_id
            and self._owned_in_flight_token
            and state.get("in_flight_request_id") == self._owned_in_flight_request_id
            and secrets.compare_digest(
                str(state.get("in_flight_owner_token", "")),
                self._owned_in_flight_token,
            )
        )

    @staticmethod
    def _clear_in_flight(state: dict[str, Any]) -> None:
        state.pop("in_flight_request_id", None)
        state.pop("in_flight_at", None)
        state.pop("in_flight_heartbeat_at", None)
        state.pop("in_flight_owner_token", None)

    def _recover_in_flight(self, state: dict[str, Any], now: datetime) -> bool:
        """Turn an interrupted dispatch into one bounded retry attempt."""
        request_id = state.get("in_flight_request_id")
        if not request_id:
            return False
        if self._owns_in_flight(state):
            return True
        try:
            lease_timestamp = state.get("in_flight_heartbeat_at") or state.get("in_flight_at")
            heartbeat_at = _as_utc(datetime.fromisoformat(lease_timestamp))
            if now - heartbeat_at < self._in_flight_lease:
                return True
        except (KeyError, TypeError, ValueError):
            pass
        state["last_result"] = "failed"
        state["last_result_at"] = now.isoformat()
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        self._clear_in_flight(state)
        self._write_state(state)
        return False

    def _read_state(self) -> dict[str, Any]:
        self._assert_safe_state_path()
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_state(self, state: dict[str, Any]) -> None:
        self._assert_safe_state_path()
        temporary = self.state_path.with_name(
            f".{self.state_path.name}.{secrets.token_hex(16)}.tmp"
        )
        descriptor = os.open(
            temporary,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, sort_keys=True, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.state_path)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def _assert_safe_state_path(self) -> None:
        """Fail closed if mutable scheduler state can leave the instance."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            resolved_parent = self.state_path.parent.resolve(strict=True)
            resolved_parent.relative_to(self.root)
        except (OSError, ValueError):
            raise ValueError(
                "Scheduler state path must stay inside the instance"
            ) from None
        if self.state_path.is_symlink():
            raise ValueError("Scheduler state file must not be a symlink")

    def acquire_dispatch_lock(self) -> str | None:
        """Atomically acquire the short evaluate-to-mark critical section."""
        self._assert_safe_state_path()
        for _ in range(2):
            token = secrets.token_hex(16)
            payload = json.dumps({"token": token, "acquired_at": _as_utc(None).isoformat()})
            try:
                descriptor = os.open(
                    self.dispatch_lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
            except FileExistsError:
                if not self._dispatch_lock_is_stale():
                    return None
                try:
                    self.dispatch_lock_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            try:
                os.write(descriptor, payload.encode("utf-8"))
                return token
            finally:
                os.close(descriptor)
        return None

    def _acquire_dispatch_lock_with_retry(self) -> str | None:
        """Wait briefly for an active evaluate/heartbeat state mutation."""
        for _ in range(100):
            token = self.acquire_dispatch_lock()
            if token is not None:
                return token
            time.sleep(0.01)
        return None

    def release_dispatch_lock(self, token: str) -> None:
        """Release only the lock instance owned by this scheduler process."""
        try:
            payload = json.loads(self.dispatch_lock_path.read_text(encoding="utf-8"))
            if payload.get("token") == token:
                self.dispatch_lock_path.unlink()
        except (OSError, json.JSONDecodeError, AttributeError):
            return

    def _dispatch_lock_is_stale(self) -> bool:
        try:
            raw_payload = self.dispatch_lock_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return True
        except OSError:
            return False
        try:
            payload = json.loads(raw_payload)
            acquired_at = _as_utc(datetime.fromisoformat(payload["acquired_at"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            # os.open(O_EXCL) creates the file before its owner can write the
            # JSON payload. Treat that observable empty/partial state as live
            # until the lease expires instead of unlinking an active lock.
            try:
                acquired_at = datetime.fromtimestamp(
                    self.dispatch_lock_path.stat().st_mtime,
                    timezone.utc,
                )
            except FileNotFoundError:
                return True
            except OSError:
                return False
        return _as_utc(None) - acquired_at >= self._in_flight_lease


def _bounded_instance_files(root: Path) -> list[tuple[str, Path]]:
    """Scan at most ``MAX_INPUT_SCAN_ENTRIES`` without following directories.

    File symlinks are resolved and accepted only when their final target stays
    inside the instance. Returning the logical relative path preserves glob
    behavior without ever hashing an outside target.
    """
    root = root.resolve()
    directories = [root]
    directory_index = 0
    files: list[tuple[str, Path]] = []
    scanned = 0
    while directory_index < len(directories) and scanned < MAX_INPUT_SCAN_ENTRIES:
        directory = directories[directory_index]
        directory_index += 1
        entries: list[os.DirEntry[str]] = []
        try:
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    if scanned >= MAX_INPUT_SCAN_ENTRIES:
                        break
                    scanned += 1
                    entries.append(entry)
        except OSError:
            continue
        for entry in sorted(entries, key=lambda item: item.name):
            logical = Path(entry.path)
            try:
                if entry.is_dir(follow_symlinks=False):
                    directories.append(logical)
                    continue
                if not (entry.is_file(follow_symlinks=False) or entry.is_symlink()):
                    continue
                resolved = logical.resolve(strict=True)
                if not _is_within(resolved, root) or not resolved.is_file():
                    continue
                relative = logical.relative_to(root).as_posix()
            except (OSError, RuntimeError, ValueError):
                continue
            files.append((relative, resolved))
    return sorted(files)


def _matches_relative_glob(relative: str, pattern: str) -> bool:
    """Match pathlib-style globs, including zero or more ``**`` segments."""
    path_parts = tuple(relative.split("/"))
    pattern_parts = tuple(pattern.replace("\\", "/").split("/"))
    states = {(0, 0)}
    visited: set[tuple[int, int]] = set()
    while states:
        path_index, pattern_index = states.pop()
        if (path_index, pattern_index) in visited:
            continue
        visited.add((path_index, pattern_index))
        if pattern_index == len(pattern_parts):
            if path_index == len(path_parts):
                return True
            continue
        part = pattern_parts[pattern_index]
        if part == "**":
            states.add((path_index, pattern_index + 1))
            if path_index < len(path_parts):
                states.add((path_index + 1, pattern_index))
        elif path_index < len(path_parts) and fnmatch.fnmatchcase(path_parts[path_index], part):
            states.add((path_index + 1, pattern_index + 1))
    return False


def _sha256(
    path: Path, *, max_bytes: int = MAX_INPUT_FILE_BYTES
) -> tuple[str, int] | None:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as source:
        while chunk := source.read(min(1024 * 1024, max_bytes - total + 1)):
            total += len(chunk)
            if total > max_bytes:
                return None
            digest.update(chunk)
    return digest.hexdigest(), total


def _has_open_approvals(path: Path) -> bool:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    entries = value.get("approvals", []) if isinstance(value, dict) else value
    return isinstance(entries, list) and any(
        isinstance(entry, dict) and str(entry.get("status", "")).lower() in {"pending", "open", "awaiting_approval"}
        for entry in entries
    )


def _as_utc(value: datetime | None) -> datetime:
    value = value or datetime.now(timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_instance_path(root: Path, relative: Any) -> Path | None:
    if not _is_safe_relative_glob(relative) or any(char in str(relative) for char in "*?["):
        return None
    candidate = (root / relative).resolve()
    return candidate if _is_within(candidate, root.resolve()) else None


def _is_safe_relative_glob(pattern: Any) -> bool:
    if (
        not isinstance(pattern, str)
        or not pattern
        or len(pattern) > MAX_INPUT_PATTERN_LENGTH
    ):
        return False
    normalised = pattern.replace("\\", "/")
    first = normalised.split("/", 1)[0]
    return not (
        Path(pattern).is_absolute()
        or normalised.startswith("/")
        or ":" in first
        or any(part == ".." for part in normalised.split("/"))
    )


def _public_required_group_id(value: Any, index: int) -> str:
    """Expose only opaque identifiers; descriptive names may contain tenant data."""
    if isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value):
        return value
    return f"group_{index}"


def run_scheduled_cycle(
    *,
    root: Path,
    agent_config: dict[str, Any],
    orchestrator: Any,
    tools: dict[str, Any],
) -> ScheduledDecision:
    """Dispatch one due schedule decision for any generated agent instance.

    The caller owns logging. Governance is deliberately not duplicated here:
    every due task is sent to the instance's supplied orchestrator.
    """
    scheduler = AdaptiveScheduler(root, agent_config)
    lock_token = scheduler.acquire_dispatch_lock()
    if lock_token is None:
        return ScheduledDecision(False, "already_enqueued")
    try:
        decision = scheduler.evaluate()
        if not decision.should_enqueue:
            return decision
        scheduler.mark_enqueued(decision)
    finally:
        scheduler.release_dispatch_lock(lock_token)
    heartbeat_stop = threading.Event()
    heartbeat = threading.Thread(
        target=_renew_lease_until_stopped,
        args=(scheduler, heartbeat_stop),
        name=f"scheduler-heartbeat-{decision.request_id}",
        daemon=True,
    )
    heartbeat.start()
    try:
        try:
            cycle_tools = {} if decision.reason == "missing_data" else tools
            result = _run_orchestrator(
                orchestrator,
                decision.task_text or "",
                cycle_tools,
                decision.request_id,
            )
        finally:
            heartbeat_stop.set()
            heartbeat.join(timeout=max(1.0, scheduler._heartbeat_interval_seconds + 1.0))
    except Exception:
        scheduler.record_result(success=False)
        raise
    scheduler.record_result(success=bool(result.success))
    return decision


def _renew_lease_until_stopped(scheduler: AdaptiveScheduler, stop: threading.Event) -> None:
    """Keep a live dispatch fresh; a failed CAS permanently stops its heartbeat."""
    while not stop.wait(scheduler._heartbeat_interval_seconds):
        if not scheduler.renew_in_flight():
            state = scheduler._read_state()
            # A non-atomic external reader/writer can expose a transient empty
            # or malformed file. Only a valid replacement owner stops renewal.
            if state and not scheduler._owns_in_flight(state):
                return


def _run_orchestrator(
    orchestrator: ScheduledOrchestrator | Any, task: str, tools: dict[str, Any], request_id: str | None
) -> Any:
    """Use request identity where the supplied compatible runner accepts it."""
    parameters = inspect.signature(orchestrator.run).parameters.values()
    supports_request_id = any(
        parameter.name == "request_id" or parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )
    if supports_request_id:
        return orchestrator.run(task, tools=tools, request_id=request_id)
    return orchestrator.run(task, tools=tools)
