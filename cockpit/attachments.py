"""Bounded, immutable attachments scoped to a conversation binding."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import threading
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentkit.contracts import ContractError
from agentkit.storage import save
from agentkit.backends import _process_result, subprocess_environment


_ID = re.compile(r"[0-9a-f]{32}\Z")
_EXTENSIONS = {"txt", "md", "csv", "json", "yaml", "yml", "log", "py", "js", "ts", "tsx", "jsx", "html", "css", "sql", "xml", "toml"}
_BINDING_KEYS = {"conversation_id", "company", "agent", "workspace"}
_MAX_BYTES = 32_768
_DOCUMENT_EXTENSIONS = {"pdf", "docx", "xlsx", "pptx"}
_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
_DOCUMENT_MAX_BYTES = 2 * 1024 * 1024
_MAX_EXTRACTED_CHARS = 48_000
_MAX_ATTACHMENTS = 20
_MAX_TOTAL_BYTES = 8 * 1024 * 1024
_EXTRACT_SLOTS = threading.BoundedSemaphore(2)
_LANGUAGE = re.compile(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*\Z")


def _byte_limit(name: str) -> int:
    extension = name.rsplit(".", 1)[-1].lower()
    return _DOCUMENT_MAX_BYTES if extension in _DOCUMENT_EXTENSIONS | _IMAGE_EXTENSIONS else _MAX_BYTES


def _extract(name: str, data: bytes) -> str:
    if name.rsplit(".", 1)[-1].lower() not in _DOCUMENT_EXTENSIONS:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ContractError("Attachment content must be valid UTF-8 text.") from exc
        if "\x00" in text:
            raise ContractError("Attachment content must not contain NUL bytes.")
        return text
    if not _EXTRACT_SLOTS.acquire(blocking=False):
        raise ContractError("Dokumentverarbeitung ausgelastet. Bitte erneut versuchen.")
    try:
        script = Path(__file__).with_name("document_extract.py").resolve()
        payload = json.dumps({"name": name, "content_base64": base64.b64encode(data).decode("ascii")})
        with tempfile.TemporaryDirectory(prefix="agentkit-document-") as directory:
            code, output, _ = _process_result(
                [sys.executable, str(script)], payload, Path(directory), 8,
                env=subprocess_environment(),
            )
        result = json.loads(output)
        if code != 0 or not isinstance(result, dict) or not isinstance(result.get("text"), str):
            raise ContractError("Dokument nicht lesbar oder zu groß; verschlüsselte Dateien und reine Scans werden nicht unterstützt.")
        text = result["text"]
        if not text.strip() or len(text) > _MAX_EXTRACTED_CHARS or "\x00" in text:
            raise ContractError("Dokument enthält keinen nutzbaren Text oder überschreitet 48.000 Zeichen.")
        return text
    except ContractError:
        raise
    except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
        raise ContractError("Dokumentverarbeitung fehlgeschlagen oder Zeitlimit überschritten.") from exc
    finally:
        _EXTRACT_SLOTS.release()


def _extract_image(name: str, data: bytes) -> tuple[str, str, str]:
    """Run bounded Windows OCR in a filtered child process."""
    if name.rsplit(".", 1)[-1].lower() not in _IMAGE_EXTENSIONS:
        raise ContractError("Only PNG and JPEG images are supported.")
    if not ((data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24)
            or (data.startswith(b"\xff\xd8") and len(data) >= 4)):
        raise ContractError("Image is corrupt or has an unsupported format.")
    if not _EXTRACT_SLOTS.acquire(blocking=False):
        raise ContractError("Bildverarbeitung ausgelastet. Bitte erneut versuchen.")
    try:
        script = Path(__file__).with_name("image_extract.py").resolve()
        payload = json.dumps({"name": name, "content_base64": base64.b64encode(data).decode("ascii")})
        environment = subprocess_environment()
        # Keep the child environment filtered while making the local package
        # importable when the cockpit is run directly from a checkout.
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory(prefix="agentkit-image-") as directory:
            code, output, _ = _process_result(
                [sys.executable, str(script)], payload, Path(directory), 12,
                env=environment,
            )
        result = json.loads(output)
        text = result.get("text") if isinstance(result, dict) else None
        method = result.get("extraction_method") if isinstance(result, dict) else None
        language = result.get("language") if isinstance(result, dict) else None
        if (code != 0 or method != "windows-ocr" or not isinstance(text, str)
                or not isinstance(language, str) or not language.strip()
                or len(language) > 64 or not _LANGUAGE.fullmatch(language) or not text.strip()
                or len(text) > _MAX_EXTRACTED_CHARS or "\x00" in text):
            raise ContractError("Bild konnte nicht gelesen werden oder Windows-OCR ist nicht verfügbar.")
        try:
            text.encode("utf-8", "strict")
            language.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise ContractError("Windows-OCR lieferte ungültige Metadaten.") from exc
        return text, method, language
    except ContractError:
        raise
    except (subprocess.TimeoutExpired, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ContractError("Bildverarbeitung fehlgeschlagen oder Zeitlimit überschritten.") from exc
    finally:
        _EXTRACT_SLOTS.release()


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ContractError(f"{label} must be a canonical 32-character hexadecimal id.")
    return value


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class Attachments:
    """Persist originals and extracted context without writing into a workspace."""

    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir)
        self.directory = self.state_dir / "attachments"
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @staticmethod
    def _binding(binding: dict) -> dict:
        if not isinstance(binding, dict) or set(binding) != _BINDING_KEYS:
            raise ContractError("Attachment binding must contain exactly conversation_id, company, agent and workspace.")
        result = {}
        for key in _BINDING_KEYS:
            value = binding[key]
            if not isinstance(value, str) or not value:
                raise ContractError(f"Attachment binding {key} must be nonempty text.")
            result[key] = value
        _identifier(result["conversation_id"], "conversation_id")
        return result

    @staticmethod
    def _name(value: Any) -> str:
        if not isinstance(value, str) or not value or len(value) > 255:
            raise ContractError("Attachment name must contain 1–255 characters.")
        if value in {".", ".."} or "/" in value or "\\" in value or Path(value).name != value:
            raise ContractError("Attachment name must be a filename without path components.")
        if any(unicodedata.category(char).startswith("C") for char in value):
            raise ContractError("Attachment name contains a control character.")
        if any(char in value for char in ':<>"|?*'):
            raise ContractError("Attachment name contains an unsupported filename character.")
        if "." not in value or value.rsplit(".", 1)[1].lower() not in _EXTENSIONS | _DOCUMENT_EXTENSIONS | _IMAGE_EXTENSIONS:
            raise ContractError("Attachment extension is not supported.")
        return value

    @staticmethod
    def _payload(payload: dict) -> tuple[str, str, bytes]:
        if not isinstance(payload, dict) or set(payload) != {"request_id", "name", "content_base64"}:
            raise ContractError("Attachment payload must contain request_id, name and content_base64.")
        request_id = _identifier(payload["request_id"], "request_id")
        name = Attachments._name(payload["name"])
        encoded = payload["content_base64"]
        if not isinstance(encoded, str):
            raise ContractError("content_base64 must be text.")
        # A base64 string larger than this cannot decode to the bounded payload.
        maximum = _byte_limit(name)
        if len(encoded) > ((maximum + 2) // 3) * 4:
            raise ContractError("Attachment exceeds its format size limit.")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ContractError("content_base64 is invalid.") from exc
        if len(data) > maximum:
            raise ContractError("Attachment exceeds its format size limit.")
        return request_id, name, data

    def _path(self, conversation_id: str, attachment_id: str) -> Path:
        return self.directory / conversation_id / (attachment_id + ".json")

    def _load(self, binding: dict, attachment_id: str) -> tuple[dict, bytes, str]:
        attachment_id = _identifier(attachment_id, "attachment_id")
        path = self._path(binding["conversation_id"], attachment_id)
        if not path.is_file():
            raise ContractError("Attachment not found.")
        try:
            with path.open("rb") as handle:
                raw = handle.read(3_500_001)
            if len(raw) > 3_500_000:
                raise ValueError
            record = json.loads(raw.decode("utf-8"))
            if not isinstance(record, dict) or record.get("id") != attachment_id:
                raise ValueError
            if record.get("binding") != binding:
                raise ContractError("Attachment binding does not match.")
            _identifier(record.get("request_id"), "request_id")
            if not isinstance(record.get("created_at"), str):
                raise ValueError
            name = self._name(record["name"])
            maximum = _byte_limit(name)
            if record.get("size", -1) < 0 or record["size"] > maximum:
                raise ValueError
            encoded = record["content_base64"]
            if not isinstance(encoded, str) or len(encoded) > ((maximum + 2) // 3) * 4:
                raise ValueError
            data = base64.b64decode(encoded, validate=True)
            digest = hashlib.sha256(data).hexdigest()
            if record.get("name") != name or record.get("sha256") != digest or record.get("size") != len(data):
                raise ValueError
            extension = name.rsplit(".", 1)[-1].lower()
            if extension in _DOCUMENT_EXTENSIONS | _IMAGE_EXTENSIONS:
                text = record.get("text")
                try:
                    text_digest = hashlib.sha256(text.encode("utf-8", "strict")).hexdigest()
                except (AttributeError, UnicodeError):
                    raise ValueError
                if (not isinstance(text, str) or not text.strip() or len(text) > _MAX_EXTRACTED_CHARS
                        or "\x00" in text or record.get("text_sha256") != text_digest):
                    raise ValueError
                if extension in _IMAGE_EXTENSIONS:
                    if not ((data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24)
                            or (data.startswith(b"\xff\xd8") and len(data) >= 4)):
                        raise ValueError
                    language = record.get("language")
                    if (record.get("extraction_method") != "windows-ocr" or not isinstance(language, str)
                            or not language.strip() or len(language) > 64 or not _LANGUAGE.fullmatch(language)):
                        raise ValueError
                    try:
                        language.encode("utf-8", "strict")
                    except UnicodeError:
                        raise ValueError
            else:
                text = _extract(name, data)
                if record.get("text") != text:
                    raise ValueError
            return record, data, text
        except ContractError:
            raise
        except (OSError, ValueError, KeyError, TypeError, UnicodeDecodeError, binascii.Error) as exc:
            raise ContractError("Attachment integrity check failed.") from exc

    def put(self, binding: dict, payload: dict) -> dict:
        binding = self._binding(binding)
        request_id, name, data = self._payload(payload)
        digest = hashlib.sha256(data).hexdigest()
        with self._lock:
            conversation_dir = self.directory / binding["conversation_id"]
            matching = None
            count = 0
            total = 0
            for path in conversation_dir.glob("*.json"):
                count += 1
                if count > _MAX_ATTACHMENTS:
                    raise ContractError("Attachment store exceeds its file limit.")
                existing, stored, _text = self._load(binding, path.stem)
                total += len(stored)
                if existing.get("request_id") != request_id:
                    continue
                if existing.get("name") == name and existing.get("sha256") == digest and existing.get("size") == len(data):
                    matching = self._metadata(existing)
                else:
                    raise ContractError("request_id already identifies another attachment.")
            if matching:
                return matching
            if count >= _MAX_ATTACHMENTS or total + len(data) > _MAX_TOTAL_BYTES:
                raise ContractError("Conversation attachment limit exceeded.")
            extraction_method = language = None
            if name.rsplit(".", 1)[-1].lower() in _IMAGE_EXTENSIONS:
                text, extraction_method, language = _extract_image(name, data)
            else:
                text = _extract(name, data)
            attachment_id = uuid.uuid4().hex
            created_at = _timestamp()
            record = {"id": attachment_id, "request_id": request_id, "name": name,
                      "size": len(data), "sha256": digest, "created_at": created_at,
                      "binding": binding, "content_base64": base64.b64encode(data).decode("ascii"),
                      "text": text, "text_sha256": hashlib.sha256(text.encode()).hexdigest()}
            if extraction_method is not None:
                record["extraction_method"] = extraction_method
                record["language"] = language
            save(self._path(binding["conversation_id"], attachment_id), record)
            return self._metadata(record)

    @staticmethod
    def _metadata(record: dict) -> dict:
        metadata = {key: record[key] for key in ("id", "name", "size", "sha256", "created_at")}
        if record.get("name", "").rsplit(".", 1)[-1].lower() in _IMAGE_EXTENSIONS:
            metadata["extraction_method"] = record["extraction_method"]
            metadata["language"] = record["language"]
        return metadata

    def read(self, binding: dict, attachment_id: str) -> dict:
        binding = self._binding(binding)
        with self._lock:
            record, _data, text = self._load(binding, attachment_id)
            return {"metadata": self._metadata(record), "text": text}

    def download(self, binding: dict, attachment_id: str) -> tuple[bytes, str]:
        binding = self._binding(binding)
        with self._lock:
            record, data, _text = self._load(binding, attachment_id)
            return data, record["name"]
