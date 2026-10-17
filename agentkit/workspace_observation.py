"""Bounded, host-owned read-only observations for Codex action workers.

Observation results are returned to the caller for ephemeral prompt context;
callers must not store their file contents in action history or checkpoints.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

from .approvals import INTERNAL_WORKSPACE_SEGMENTS, _canonical_windows_path, safe_workspace_path
from .contracts import ContractError
from .test_execution import _open_source_handle


OBSERVATION_TOOLS = frozenset({"read_file", "list_files", "inspect_git"})
MAX_FILE_BYTES = 2_000_000
MAX_READ_CHARS = 12_000
MAX_READ_LINES = 200
MAX_LIST_ENTRIES = 200
MAX_LIST_CHARS = 12_000
MAX_GIT_STATUS_CHARS = 12_000
MAX_GIT_DIFF_CHARS = 24_000
MAX_GIT_BLOB_BYTES = 700_000
MAX_GIT_PATHS = 32
_SENSITIVE_DIRS = frozenset({
    ".aws", ".azure", ".codex", ".credentials", ".ssh", "certs", "certificates",
    "credentials", "private", "private_keys", "secret", "secrets", "token", "tokens",
})
_SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".p7b", ".p7c", ".p8", ".crt", ".cer")
_SENSITIVE_NAMES = frozenset({
    "credentials.json", "secrets.json", "secret.json", "token.txt", "id_rsa", "id_dsa",
    "id_ecdsa", "id_ed25519", "identity", "identity.pem",
})


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _sensitive_path(relative: str) -> bool:
    parts = [part.casefold() for part in relative.split("/") if part]
    if any(part in _SENSITIVE_DIRS for part in parts):
        return True
    filename = parts[-1] if parts else ""
    return (filename.startswith(".env") or filename in _SENSITIVE_NAMES
            or filename.endswith(_SENSITIVE_SUFFIXES))


def _relative_path(value: object, *, allow_root: bool = False) -> str:
    if not isinstance(value, str) or len(value) > 500 or "\\" in value or "\x00" in value:
        raise ContractError("Observation path must be bounded relative POSIX text.")
    if value == "" and allow_root:
        return ""
    parts = value.split("/")
    if (not value or len(parts) > 16 or any(part in {"", ".", ".."} for part in parts)
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ContractError("Observation path is not a canonical relative workspace path.")
    if any(part.endswith((" ", ".")) for part in parts):
        raise ContractError("Observation path is not a canonical portable path.")
    return value


def _workspace_target(workspace: Path, relative: str, *, allow_root: bool = False) -> Path:
    root = _canonical_windows_path(Path(workspace).resolve(strict=True))
    if not root.is_dir():
        raise ContractError("Observation workspace does not exist.")
    if relative == "" and allow_root:
        return root
    if _sensitive_path(relative):
        raise ContractError("Sensitive workspace paths are not observable.")
    return safe_workspace_path(root, relative)


def _read_file(workspace: Path, arguments: dict) -> str:
    if set(arguments) - {"path", "start_line", "max_lines"} or "path" not in arguments:
        return _json({"error": "invalid_read_arguments"})
    relative = _relative_path(arguments["path"])
    start = arguments.get("start_line", 1)
    limit = arguments.get("max_lines", 100)
    if (type(start) is not int or type(limit) is not int or start < 1
            or not 1 <= limit <= MAX_READ_LINES):
        return _json({"error": "invalid_read_range", "hint": "Use start_line >= 1 and max_lines in 1..200."})
    root = _canonical_windows_path(Path(workspace).resolve(strict=True))
    try:
        canonical_target = safe_workspace_path(root, relative)
        canonical_relative = canonical_target.relative_to(root).as_posix()
    except (ContractError, OSError, ValueError):
        return _json({"error": "file_not_readable"})
    if _sensitive_path(relative) or _sensitive_path(canonical_relative):
        return _json({"error": "sensitive_path_not_observable"})
    try:
        raw = _read_canonical_file(root, canonical_target, canonical_relative)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp1252")
        if "\x00" in text:
            return _json({"error": "file_not_readable"})
    except (ContractError, OSError, UnicodeDecodeError):
        return _json({"error": "file_not_readable"})
    lines = text.splitlines(keepends=True)
    total = len(lines)
    if start > total and not (start == 1 and total == 0):
        return _json({"error": "start_line_out_of_range", "total_lines": total})
    selected: list[str] = []
    used = 0
    end_index = min(total, start - 1 + limit)
    for line in lines[start - 1:end_index]:
        if len(line) > MAX_READ_CHARS and not selected:
            return _json({"error": "line_exceeds_observation_budget", "line": start})
        if used + len(line) > MAX_READ_CHARS:
            break
        selected.append(line)
        used += len(line)
    end = start + len(selected) - 1
    truncated = end < total
    return _json({
        "path": relative, "start_line": start, "end_line": end, "total_lines": total,
        "next_line": end + 1 if truncated else None, "truncated": truncated,
        "content": "".join(selected),
    })


def _read_canonical_file(root: Path, target: Path, relative: str) -> bytes:
    """Read a regular file from its canonical path so aliases cannot bypass filtering."""
    fd = _open_source_handle(root, target, relative)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_FILE_BYTES:
            raise ContractError("Observation accepts only bounded regular files without link aliases.")
        chunks = []
        remaining = MAX_FILE_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                       before.st_ctime_ns, before.st_nlink)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                      after.st_ctime_ns, after.st_nlink)
    data = b"".join(chunks)
    if len(data) != before.st_size or before_identity != after_identity:
        raise ContractError("Workspace changed while the observation was read.")
    return data


def _directory_entries(root: Path, target: Path, relative: str) -> list[tuple[str, bool, bool]]:
    """Enumerate from a pinned directory handle; tuple is name, is_dir, is_link."""
    if os.name == "nt":
        import ctypes

        class FileTime(ctypes.Structure):
            _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]

        class ByHandleInfo(ctypes.Structure):
            _fields_ = [
                ("attributes", ctypes.c_uint32), ("creation", FileTime),
                ("access", FileTime), ("write", FileTime), ("volume", ctypes.c_uint32),
                ("size_high", ctypes.c_uint32), ("size_low", ctypes.c_uint32),
                ("links", ctypes.c_uint32), ("index_high", ctypes.c_uint32),
                ("index_low", ctypes.c_uint32),
            ]

        class IoStatusBlock(ctypes.Structure):
            _fields_ = [("status", ctypes.c_void_p), ("information", ctypes.c_size_t)]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        create_file.restype = ctypes.c_void_p
        get_info = kernel32.GetFileInformationByHandle
        get_info.argtypes = [ctypes.c_void_p, ctypes.POINTER(ByHandleInfo)]
        get_info.restype = ctypes.c_int
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_int
        handle = create_file(str(target), 0x00000001, 0x00000007, None, 3,
                             0x00200000 | 0x02000000, None)  # list directory; open reparse point
        if handle == ctypes.c_void_p(-1).value:
            raise OSError(ctypes.get_last_error(), "Could not safely open observation directory")
        try:
            info = ByHandleInfo()
            if not get_info(handle, ctypes.byref(info)):
                raise OSError(ctypes.get_last_error(), "Could not inspect observation directory")
            if not info.attributes & 0x10 or info.attributes & 0x400:
                raise ContractError("Linked or non-directory paths cannot be listed.")
            get_final = kernel32.GetFinalPathNameByHandleW
            get_final.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
            get_final.restype = ctypes.c_uint32
            buffer = ctypes.create_unicode_buffer(32768)
            length = get_final(handle, buffer, len(buffer), 0)
            if not length or length >= len(buffer):
                raise OSError(ctypes.get_last_error(), "Could not verify observation directory")
            actual = buffer.value
            if actual.startswith("\\\\?\\UNC\\"):
                actual = "\\\\" + actual[8:]
            elif actual.startswith("\\\\?\\"):
                actual = actual[4:]
            if os.path.normcase(os.path.normpath(actual)) != os.path.normcase(os.path.normpath(str(target))):
                raise ContractError("Observation directory changed canonical identity.")

            class NtEntry(ctypes.Structure):
                _fields_ = [
                    ("next", ctypes.c_uint32), ("index", ctypes.c_uint32),
                    ("creation", ctypes.c_int64), ("access", ctypes.c_int64),
                    ("write", ctypes.c_int64), ("change", ctypes.c_int64),
                    ("end_of_file", ctypes.c_int64), ("allocation", ctypes.c_int64),
                    ("attributes", ctypes.c_uint32), ("name_length", ctypes.c_uint32),
                    ("name", ctypes.c_wchar * 1),
                ]

            ntdll = ctypes.WinDLL("ntdll")
            query = ntdll.NtQueryDirectoryFile
            query.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                              ctypes.c_void_p, ctypes.POINTER(IoStatusBlock), ctypes.c_void_p,
                              ctypes.c_uint32, ctypes.c_int, ctypes.c_ubyte, ctypes.c_void_p,
                              ctypes.c_ubyte]
            query.restype = ctypes.c_long
            results = []
            restart = 1
            while True:
                data = ctypes.create_string_buffer(64 * 1024)
                iosb = IoStatusBlock()
                status = query(handle, None, None, None, ctypes.byref(iosb), data,
                               len(data), 1, 0, None, restart) & 0xFFFFFFFF
                restart = 0
                if status == 0x80000006:  # STATUS_NO_MORE_FILES
                    break
                if status not in {0, 0x80000005}:  # success or STATUS_BUFFER_OVERFLOW
                    raise OSError(f"NtQueryDirectoryFile failed: {status:08x}")
                offset = 0
                while offset < iosb.information:
                    entry = ctypes.cast(ctypes.byref(data, offset), ctypes.POINTER(NtEntry)).contents
                    if entry.name_length % 2:
                        raise OSError("Malformed directory entry name")
                    name_start = offset + NtEntry.name.offset
                    name = bytes(data[name_start:name_start + entry.name_length]).decode("utf-16-le", "strict")
                    attrs = entry.attributes
                    results.append((name, bool(attrs & 0x10), bool(attrs & 0x400)))
                    if not entry.next:
                        break
                    offset += entry.next
                if len(results) > MAX_LIST_ENTRIES:
                    break
            return results
        finally:
            close_handle(handle)

    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory_flag is None or os.open not in getattr(os, "supports_dir_fd", set()):
        raise ContractError("This host cannot safely enumerate observation directories.")
    flags = os.O_RDONLY | directory_flag | nofollow | getattr(os, "O_CLOEXEC", 0)
    parent_fd = os.open(str(root), flags)
    try:
        for part in relative.split("/") if relative else ():
            next_fd = os.open(part, flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        results = []
        with os.scandir(parent_fd) as scan:
            for item in scan:
                info = os.stat(item.name, dir_fd=parent_fd, follow_symlinks=False)
                results.append((item.name, stat.S_ISDIR(info.st_mode), stat.S_ISLNK(info.st_mode)))
                if len(results) > MAX_LIST_ENTRIES:
                    break
        return results
    finally:
        os.close(parent_fd)


def _list_files(workspace: Path, arguments: dict) -> str:
    if set(arguments) - {"path"}:
        return _json({"error": "invalid_list_arguments"})
    relative = _relative_path(arguments.get("path", ""), allow_root=True)
    root = _canonical_windows_path(Path(workspace).resolve(strict=True))
    try:
        directory = _workspace_target(root, relative, allow_root=True)
        canonical_relative = directory.relative_to(root).as_posix() if relative else ""
        if _sensitive_path(canonical_relative):
            return _json({"error": "sensitive_path_not_observable"})
        # Enumeration is anchored to a no-follow directory handle and bounded
        # before sorting so a large workspace cannot force unbounded metadata work.
        entries = []
        raw_entries = _directory_entries(root, directory, canonical_relative)
        truncated_by_cap = len(raw_entries) > MAX_LIST_ENTRIES
        for name, is_directory, is_link in raw_entries[:MAX_LIST_ENTRIES]:
            if name in {".", ".."}:
                continue
            folded_name = name.casefold()
            item_relative = f"{relative}/{name}" if relative else name
            if (folded_name in INTERNAL_WORKSPACE_SEGMENTS or _sensitive_path(name)
                    or _sensitive_path(item_relative) or is_link):
                continue
            entries.append({"path": item_relative, "kind": "dir" if is_directory else "file"})
        entries.sort(key=lambda item: item["path"].casefold())
    except (ContractError, OSError, ValueError):
        return _json({"error": "directory_not_readable"})
    bounded: list[dict] = []
    chars = 2
    for entry in entries:
        size = len(entry["path"]) + len(entry["kind"]) + 24
        if chars + size > MAX_LIST_CHARS:
            break
        bounded.append(entry)
        chars += size
    return _json({"path": relative or ".", "entries": bounded,
                  "truncated": truncated_by_cap or len(bounded) < len(entries)})


def _inspect_git(workspace: Path, timeout: float, *, process_result: Callable,
                  environment_factory: Callable, redact: str = "") -> str:
    root = _canonical_windows_path(Path(workspace).resolve(strict=True))
    if not root.is_dir():
        return _json({"status": "unavailable", "reason": "workspace_missing"})
    executable = shutil.which("git")
    if not executable:
        return _json({"status": "unavailable", "reason": "git_not_installed"})
    environment = environment_factory()
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    command = [executable, "--literal-pathspecs", "-c", "core.fsmonitor=false",
               "-c", "core.pager=cat"]
    deadline = time.monotonic() + timeout

    def run(args: list[str], *, cwd: Path = root):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(command, timeout)
        return process_result(command + args, "", cwd, remaining, env=environment)

    try:
        code, top, _ = run(["rev-parse", "--show-toplevel"])
        if code or Path(top.strip()).resolve() != root:
            return _json({"status": "unavailable", "reason": "workspace_is_not_git_root"})
        status_code, status_raw, _ = run(["status", "--porcelain=v1", "-z", "--no-renames",
                                         "--untracked-files=normal"])
    except subprocess.TimeoutExpired:
        return _json({"status": "unavailable", "reason": "git_inspection_timeout"})
    except (OSError, RuntimeError, ContractError):
        return _json({"status": "unavailable", "reason": "git_inspection_failed"})
    if status_code:
        return _json({"status": "unavailable", "reason": "git_inspection_failed"})
    status_parts = status_raw.split("\0")
    safe_status = []
    safe_paths: dict[str, str] = {}
    filtered_changes_present = False
    index = 0
    status_truncated = False
    processed_paths = 0
    while index < len(status_parts) and status_parts[index]:
        if processed_paths >= MAX_GIT_PATHS:
            status_truncated = True
            break
        record = status_parts[index]
        index += 1
        processed_paths += 1
        if len(record) < 4 or record[2] != " ":
            return _json({"status": "unavailable", "reason": "git_status_unparseable"})
        path = record[3:]
        if record[:2].strip() in {"R", "C"}:
            index += 1  # --no-renames should prevent this; fail closed below if malformed.
            return _json({"status": "unavailable", "reason": "git_status_unparseable"})
        if _git_path_observable(root, path):
            safe_status.append(f"{record[:2]} {path}\n")
            if record[:2] != "??":
                safe_paths[path] = record[:2]
        else:
            filtered_changes_present = True
    status = "".join(safe_status)
    diff_pieces = []
    diff_length = 0
    diff_truncated = False
    for path, state in safe_paths.items():
        try:
            piece = _safe_git_text_diff(root, path, state, run)
        except subprocess.TimeoutExpired:
            return _json({"status": "unavailable", "reason": "git_inspection_timeout"})
        except (OSError, RuntimeError, ContractError):
            return _json({"status": "unavailable", "reason": "git_inspection_failed"})
        remaining_chars = MAX_GIT_DIFF_CHARS - diff_length
        if len(piece) > remaining_chars:
            diff_pieces.append(piece[:remaining_chars])
            diff_length = MAX_GIT_DIFF_CHARS
            diff_truncated = True
            break
        diff_pieces.append(piece)
        diff_length += len(piece)
    diff = "".join(diff_pieces)
    if redact:
        status = status.replace(redact, "[REDACTED]")
        diff = diff.replace(redact, "[REDACTED]")
    truncated = (status_truncated or len(status) > MAX_GIT_STATUS_CHARS or diff_truncated
                 or len(diff) > MAX_GIT_DIFF_CHARS)
    return _json({"status": "partial" if filtered_changes_present or truncated else "ok",
                  "filtered_changes_present": filtered_changes_present,
                  "git_status": status[:MAX_GIT_STATUS_CHARS],
                  "diff_head": diff[:MAX_GIT_DIFF_CHARS],
                  "truncated": truncated})


def _safe_git_text_diff(root: Path, path: str, state: str, run: Callable) -> str:
    """Compare a safely captured worktree file with a Git object, never reread it through Git."""
    if not _git_path_observable(root, path):
        raise ContractError("Git path became unsafe before source capture.")
    relative = _relative_path(path)
    target = safe_workspace_path(root, relative)
    canonical_relative = target.relative_to(root).as_posix()
    if _sensitive_path(canonical_relative):
        raise ContractError("Git path resolved to a sensitive canonical path.")

    tree_code, tree_raw, _ = run(["ls-tree", "-r", "-z", "--full-tree", "HEAD", "--", path])
    if tree_code:
        raise ContractError("Could not identify the immutable Git baseline object.")
    baseline_oid = None
    for item in tree_raw.split("\0"):
        if not item:
            continue
        metadata, separator, item_path = item.partition("\t")
        fields = metadata.split(" ")
        if separator and item_path == path and len(fields) == 3 and fields[1] == "blob":
            baseline_oid = fields[2]
            break

    baseline = b""
    if baseline_oid:
        size_code, size_text, _ = run(["cat-file", "-s", baseline_oid])
        if size_code or not size_text.strip().isdigit():
            raise ContractError("Git baseline size was unavailable.")
        size = int(size_text.strip())
        if size > MAX_GIT_BLOB_BYTES:
            raise ContractError("Git baseline exceeds the bounded text-diff size.")
        blob_code, blob_text, _ = run(["cat-file", "blob", baseline_oid])
        if blob_code:
            raise ContractError("Git baseline object could not be read.")
        baseline = blob_text.encode("utf-8")
        if len(baseline) != size:
            raise ContractError("Git baseline is not bounded valid UTF-8 text.")

    try:
        current = _read_canonical_file(root, target, canonical_relative)
    except FileNotFoundError:
        if "D" not in state:
            raise ContractError("Changed Git path disappeared before safe capture.")
        current = b""
    if len(current) > MAX_GIT_BLOB_BYTES:
        raise ContractError("Current Git path exceeds the bounded text-diff size.")
    if b"\x00" in baseline or b"\x00" in current:
        raise ContractError("Binary Git changes are omitted fail-closed.")
    try:
        baseline.decode("utf-8")
        current.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError("Binary or non-UTF-8 Git changes are omitted fail-closed.") from exc
    with tempfile.TemporaryDirectory(prefix="agentkit-git-observation-") as private_dir:
        capture_root = Path(private_dir).resolve(strict=True)
        if capture_root == root or root in capture_root.parents:
            raise ContractError("Private Git diff captures must remain outside the workspace.")
        before_path = capture_root / "before"
        after_path = capture_root / "after"
        before_path.write_bytes(baseline)
        after_path.write_bytes(current)
        code, output, _ = run([
            "diff", "--no-index", "--no-ext-diff", "--no-textconv", "--no-renames",
            "--no-color", "--", before_path.name, after_path.name,
        ], cwd=capture_root)
        if code not in {0, 1}:
            raise ContractError("Bounded Git comparison failed.")
        rewritten = []
        for line in output.splitlines(keepends=True):
            if line.startswith("diff --git a/before b/after"):
                line = line.replace("a/before b/after", f"a/{path} b/{path}", 1)
            elif line.startswith("--- a/before"):
                line = line.replace("--- a/before", f"--- a/{path}", 1)
            elif line.startswith("+++ b/after"):
                line = line.replace("+++ b/after", f"+++ b/{path}", 1)
            rewritten.append(line)
        return "".join(rewritten)


def _git_path_observable(root: Path, value: str) -> bool:
    try:
        relative = _relative_path(value)
        if _sensitive_path(relative):
            return False
        lexical = root
        for part in relative.split("/"):
            lexical = lexical / part
            try:
                if lexical.is_symlink() or bool(getattr(lexical, "is_junction", lambda: False)()):
                    return False
            except OSError:
                return False
        target = safe_workspace_path(root, relative)
        canonical_relative = target.relative_to(root).as_posix()
        if _sensitive_path(canonical_relative):
            return False
        try:
            if target.is_symlink() or bool(getattr(target, "is_junction", lambda: False)()):
                return False
        except OSError:
            return False
        return True
    except (ContractError, OSError, ValueError):
        return False


def run_workspace_observation(tool: str, arguments: dict, context: dict, timeout: float, *,
                              process_result: Callable, environment_factory: Callable,
                              redact: str = "") -> str:
    """Run a fixed observation; accepts no shell, executable, or command arguments."""
    if tool not in OBSERVATION_TOOLS or not isinstance(arguments, dict) or timeout <= 0:
        raise ContractError("Invalid workspace observation request.")
    workspace = Path(context.get("workspace", ""))
    if tool == "read_file":
        return _read_file(workspace, arguments)
    if tool == "list_files":
        return _list_files(workspace, arguments)
    if arguments:
        raise ContractError("Git observation accepts no model-controlled arguments.")
    return _inspect_git(workspace, timeout, process_result=process_result,
                        environment_factory=environment_factory, redact=redact)
