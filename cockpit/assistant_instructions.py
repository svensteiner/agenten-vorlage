"""Bounded, atomic assistant instruction document access.

The cockpit exposes the assistant's SOUL.md as a small versioned document.  This
module deliberately contains no agent discovery or HTTP concerns; callers must
first validate that a path is a registered pack.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from agentkit.contracts import ContractError


READ_LIMIT = 64 * 1024
WRITE_LIMIT = 32_000
_REVISION = re.compile(r"[0-9a-f]{64}\Z")


class InstructionConflict(ContractError):
    """The document changed since the caller's expected revision."""


@dataclass(frozen=True)
class InstructionDocument:
    raw: bytes
    text: str
    revision: str


def validate_revision(value: object) -> str:
    if not isinstance(value, str) or not _REVISION.fullmatch(value):
        raise ContractError("revision must be a 64-character lowercase SHA-256 hex digest.")
    return value


def validate_text(value: object) -> tuple[str, bytes]:
    if not isinstance(value, str):
        raise ContractError("text must be UTF-8 text.")
    if "\x00" in value:
        raise ContractError("text must not contain NUL characters.")
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeError as exc:
        raise ContractError("text must be valid UTF-8 text.") from exc
    if len(encoded) > WRITE_LIMIT:
        raise ContractError("text exceeds the 32,000-byte instruction limit.")
    if not value.strip():
        raise ContractError("text must not be blank.")
    return value, encoded


def read_document(pack: Path) -> InstructionDocument:
    soul = pack / "SOUL.md"
    if soul.is_symlink() or not soul.is_file():
        raise ContractError("SOUL.md must be a regular file, not a link.")
    try:
        with soul.open("rb") as stream:
            raw = stream.read(READ_LIMIT + 1)
    except OSError as exc:
        raise ContractError("SOUL.md could not be read.") from exc
    if len(raw) > READ_LIMIT:
        raise ContractError("SOUL.md exceeds the 64 KiB read limit.")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise ContractError("SOUL.md must be valid UTF-8.") from exc
    return InstructionDocument(raw, text, hashlib.sha256(raw).hexdigest())


def replace_document(
    pack: Path,
    text: object,
    expected_revision: object,
    *,
    storage_writer: Callable[[Path, bytes], None] | None = None,
) -> InstructionDocument:
    _, encoded = validate_text(text)
    expected = validate_revision(expected_revision)
    current = read_document(pack)
    # A retry that already achieved the requested bytes is idempotent even if
    # the caller retained an older revision.
    if current.raw == encoded:
        return current
    if current.revision != expected:
        raise InstructionConflict("Instruction revision conflict; reload before editing.")

    soul = pack / "SOUL.md"
    if soul.is_symlink() or not soul.is_file():
        raise ContractError("SOUL.md must be a regular file, not a link.")
    if storage_writer is not None:
        storage_writer(soul, encoded)
        return read_document(pack)
    fd, temporary = tempfile.mkstemp(prefix=".SOUL.", suffix=".tmp", dir=pack)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        # Recheck immediately before replace so a link cannot be followed if
        # another local process altered the target while we wrote the temp file.
        if soul.is_symlink() or not soul.is_file():
            raise ContractError("SOUL.md must be a regular file, not a link.")
        os.replace(temporary, soul)
        try:
            directory_fd = os.open(pack, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # Directory fsync is unavailable on some Windows filesystems; the
            # file itself has already been flushed before the atomic replace.
            pass
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return read_document(pack)

