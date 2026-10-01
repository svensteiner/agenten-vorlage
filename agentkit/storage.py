"""Atomic checkpoints and process locks; no shared append-only JSON races."""

from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable


def _replace_checkpoint(temp: str, target: Path) -> None:
    """Retry short Windows sharing violations without changing ACLs.

    Windows scanners and a concurrently closing reader can briefly deny an
    atomic replacement.  A bounded retry preserves the atomic operation and
    still surfaces a persistent permission failure to the caller.
    """
    attempts = 6 if os.name == "nt" else 1
    for attempt in range(attempts):
        try:
            os.replace(temp, target)
            return
        except PermissionError:
            if attempt + 1 == attempts:
                raise
            time.sleep(0.05 * (2 ** attempt))


def save(
    path: Path,
    value: dict,
    *,
    writer: Callable[[Path, bytes], None] | None = None,
) -> None:
    encoded = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if writer is not None:
        writer(path, encoded)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".checkpoint-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        _replace_checkpoint(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@contextmanager
def lock(path: Path):
    """Released by the OS on process exit, including crashes. Do not delete the lock file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(f"Workspace/run is already in use: {path}") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)
