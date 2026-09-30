"""Bounded Windows OCR orchestrator for PNG/JPEG attachments."""
from __future__ import annotations

import base64
import binascii
import json
import os
import subprocess
import sys
import re
from pathlib import Path

try:
    from agentkit.contracts import ContractError
except ImportError:  # direct isolated CLI invocation
    class ContractError(ValueError):
        pass

MAX_COMPRESSED = 2 * 1024 * 1024
MAX_DIMENSION = 4096
MAX_PIXELS = 8_000_000
MAX_TEXT = 48_000


def _dimensions(name: str, data: bytes) -> tuple[int, int]:
    ext = name.rsplit(".", 1)[-1].lower()
    if ext == "png":
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[8:12] != b"\x00\x00\x00\r" or data[12:16] != b"IHDR":
            raise ContractError("Image signature does not match PNG.")
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        offset = 8
        while offset + 12 <= len(data):
            length = int.from_bytes(data[offset:offset + 4], "big")
            if length > len(data) - offset - 12:
                raise ContractError("Malformed PNG.")
            chunk = data[offset + 4:offset + 8]
            if chunk == b"acTL":
                raise ContractError("Animated PNG is not supported.")
            offset += length + 12
            if chunk == b"IEND":
                return width, height
        raise ContractError("Malformed PNG.")
    if ext == "jpg" or ext == "jpeg":
        if not data.startswith(b"\xff\xd8"):
            raise ContractError("Image signature does not match JPEG.")
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            index += 2
            if marker in (0xD8, 0xD9):
                continue
            if index + 2 > len(data):
                break
            size = int.from_bytes(data[index:index + 2], "big")
            if size < 2 or index + size > len(data):
                raise ContractError("Malformed JPEG.")
            if marker in set(range(0xC0, 0xC4)) | set(range(0xC5, 0xC8)) | set(range(0xC9, 0xCC)) | set(range(0xCD, 0xD0)):
                return int.from_bytes(data[index + 5:index + 7], "big"), int.from_bytes(data[index + 3:index + 5], "big")
            index += size
        raise ContractError("JPEG dimensions are missing.")
    raise ContractError("Only PNG and JPEG images are supported.")


def extract_image(name: str, data: bytes) -> dict:
    if sys.platform != "win32":
        raise ContractError("Windows OCR is unavailable on this host.")
    if not isinstance(name, str) or not isinstance(data, bytes) or name.rsplit(".", 1)[-1].lower() not in {"png", "jpg", "jpeg"}:
        raise ContractError("Only PNG and JPEG images are supported.")
    if len(data) > MAX_COMPRESSED:
        raise ContractError("Image exceeds the 2 MiB compressed limit.")
    width, height = _dimensions(name, data)
    if not width or not height or width > MAX_DIMENSION or height > MAX_DIMENSION or width * height > MAX_PIXELS:
        raise ContractError("Image dimensions exceed the OCR limit.")
    payload = json.dumps({"name": name, "content_base64": base64.b64encode(data).decode("ascii")}, ensure_ascii=False)
    script = Path(__file__).with_name("image_ocr.ps1").resolve()
    command = [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(script)]
    try:
        completed = subprocess.run(command, input=payload, capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=15, check=False, env={"SystemRoot": os.environ.get("SystemRoot", r"C:\Windows")})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ContractError("Windows OCR failed or timed out.") from exc
    if completed.returncode != 0:
        raise ContractError("Windows OCR failed.")
    try:
        result = json.loads(completed.stdout)
        if not isinstance(result, dict):
            raise ValueError
        text = result.get("text")
        language = result.get("language")
        if (result.get("extraction_method") != "windows-ocr" or not isinstance(text, str)
                or not isinstance(language, str) or not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", language)
                or len(language) > 64 or not text.strip() or len(text) > MAX_TEXT or "\x00" in text):
            raise ValueError
        return {"text": text, "extraction_method": "windows-ocr", "language": language}
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ContractError("Windows OCR returned invalid text.") from exc


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(3 * 1024 * 1024 + 1)
        if len(raw) > 3 * 1024 * 1024:
            raise ContractError("Input is too large.")
        request = json.loads(raw.decode("utf-8"))
        name = request.get("name") if isinstance(request, dict) else None
        encoded = request.get("content_base64") if isinstance(request, dict) else None
        if not isinstance(name, str) or not isinstance(encoded, str):
            raise ContractError("name and content_base64 are required.")
        data = base64.b64decode(encoded, validate=True)
        sys.stdout.buffer.write((json.dumps(extract_image(name, data), ensure_ascii=False) + "\n").encode("utf-8"))
        return 0
    except (ContractError, ValueError, TypeError, UnicodeError, binascii.Error):
        print(json.dumps({"error": "image extraction failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
