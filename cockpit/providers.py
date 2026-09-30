"""Local provider credentials with Windows CurrentUser DPAPI protection."""

from __future__ import annotations

import base64
import binascii
import ctypes
import ctypes.wintypes as wintypes
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any

from agentkit.contracts import ContractError
from agentkit.storage import save


_MAX_KEY = 512
_DPAPI_UI_FORBIDDEN = 0x1


def _valid_key(value: Any) -> bool:
    return (isinstance(value, str) and 0 < len(value) <= _MAX_KEY and value.isascii()
            and not any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value))


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


class _Dpapi:
    def __init__(self):
        self.available = sys.platform == "win32"
        if not self.available:
            return
        try:
            self.crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
            self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self.protect = self.crypt32.CryptProtectData
            self.unprotect = self.crypt32.CryptUnprotectData
            self.protect.argtypes = [ctypes.POINTER(_DATA_BLOB), wintypes.LPCWSTR,
                                     ctypes.POINTER(_DATA_BLOB), wintypes.LPVOID,
                                     wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(_DATA_BLOB)]
            self.unprotect.argtypes = [ctypes.POINTER(_DATA_BLOB), ctypes.POINTER(wintypes.LPWSTR),
                                       ctypes.POINTER(_DATA_BLOB), wintypes.LPVOID,
                                       wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(_DATA_BLOB)]
            self.protect.restype = wintypes.BOOL
            self.unprotect.restype = wintypes.BOOL
            self.kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
            self.kernel32.LocalFree.restype = wintypes.HLOCAL
        except (AttributeError, OSError):
            self.available = False

    @staticmethod
    def _input(data: bytes):
        buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        return _DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer

    def protect_bytes(self, data: bytes) -> bytes:
        if not self.available:
            raise RuntimeError("Windows DPAPI is unavailable.")
        source, keepalive = self._input(data)
        result = _DATA_BLOB()
        if not self.protect(ctypes.byref(source), None, None, None, None,
                            _DPAPI_UI_FORBIDDEN, ctypes.byref(result)):
            raise OSError(ctypes.get_last_error())
        try:
            return ctypes.string_at(result.pbData, result.cbData)
        finally:
            self.kernel32.LocalFree(result.pbData)

    def unprotect_bytes(self, data: bytes) -> bytes:
        if not self.available:
            raise RuntimeError("Windows DPAPI is unavailable.")
        source, keepalive = self._input(data)
        result = _DATA_BLOB()
        description = wintypes.LPWSTR()
        if not self.unprotect(ctypes.byref(source), ctypes.byref(description), None, None, None,
                              _DPAPI_UI_FORBIDDEN, ctypes.byref(result)):
            raise OSError(ctypes.get_last_error())
        try:
            return ctypes.string_at(result.pbData, result.cbData)
        finally:
            self.kernel32.LocalFree(result.pbData)
            if description:
                self.kernel32.LocalFree(description)


class ProviderSettings:
    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir)
        self.path = self.state_dir / "providers" / "deepseek.json"
        self._dpapi = _Dpapi()
        self._lock = threading.RLock()

    @property
    def storage_available(self) -> bool:
        return self._dpapi.available

    @staticmethod
    def _environment_key() -> str | None:
        value = os.environ.get("DEEPSEEK_API_KEY")
        return value if _valid_key(value) else None

    def _stored_key(self) -> tuple[bool, str | None]:
        try:
            self.path.lstat()
        except FileNotFoundError:
            return False, None
        except OSError:
            return True, None
        if not self.storage_available:
            return True, None
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                raw = stream.read(4097)
            if len(raw) > 4096:
                return True, None
            record = json.loads(raw)
            encrypted = (record.get("protected") if isinstance(record, dict) and record.get("version") == 1 else None)
            if not isinstance(encrypted, str):
                return True, None
            plaintext = self._dpapi.unprotect_bytes(base64.b64decode(encrypted, validate=True))
            value = plaintext.decode("ascii")
            return True, value if _valid_key(value) else None
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, binascii.Error):
            return True, None

    def status(self) -> dict:
        with self._lock:
            present, stored = self._stored_key()
            if present:
                result = {"configured": stored is not None, "source": "stored" if stored is not None else "none",
                          "storage_available": self.storage_available}
                if stored is None:
                    result["error"] = "Gespeicherter Schlüssel kann nicht gelesen werden. Bitte ersetzen oder entfernen."
                return result
            environment = self._environment_key()
            return {"configured": environment is not None, "source": "environment" if environment else "none",
                    "storage_available": self.storage_available}

    def api_key(self) -> str:
        with self._lock:
            present, stored = self._stored_key()
            if present:
                if stored is None:
                    raise ContractError("Stored provider setting is invalid.")
                return stored
            return self._environment_key() or ""

    def save(self, api_key: str) -> None:
        if not _valid_key(api_key):
            raise ContractError("DeepSeek API key must be 1–512 ASCII characters without whitespace or control characters.")
        with self._lock:
            if not self.storage_available:
                raise ContractError("Protected provider storage is unavailable on this platform.")
            encrypted = self._dpapi.protect_bytes(api_key.encode("ascii"))
            save(self.path, {"version": 1, "protected": base64.b64encode(encrypted).decode("ascii")})

    def clear(self) -> None:
        with self._lock:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
