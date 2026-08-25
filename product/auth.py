"""Password hashing and signed session tokens (no extra JWT dependency)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

import re

from . import config

_PBKDF_ROUNDS = 120_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF_ROUNDS)
    return "pbkdf2$%s$%s" % (base64.b64encode(salt).decode("ascii"), base64.b64encode(dk).decode("ascii"))


def verify_password(password: str, stored: str) -> bool:
    try:
        kind, salt_b64, hash_b64 = stored.split("$", 2)
    except ValueError:
        return False
    if kind != "pbkdf2":
        return False
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(hash_b64)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF_ROUNDS)
    return hmac.compare_digest(dk, expected)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def validate_password(password: str, email: str = "") -> str | None:
    """Return an error message, or None if the password is acceptable."""
    if len(password or "") < 10:
        return "Passwort mindestens 10 Zeichen."
    if email and password.strip().lower() == email.strip().lower():
        return "Passwort darf nicht der E-Mail entsprechen."
    if not re.search(r"[A-Za-zÄÖÜäöüß]", password) or not re.search(r"[0-9]", password):
        return "Passwort braucht Buchstaben und Ziffern."
    return None


def issue_token(payload: dict[str, Any], ttl: int | None = None) -> str:
    body = dict(payload)
    body["exp"] = int(time.time()) + int(ttl or config.TOKEN_TTL_SECONDS)
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(config.SECRET.encode("utf-8"), raw, hashlib.sha256).digest()
    return _b64url(raw) + "." + _b64url(sig)


def read_token(token: str) -> dict[str, Any] | None:
    try:
        raw_b64, sig_b64 = token.split(".", 1)
        raw = _b64url_decode(raw_b64)
        sig = _b64url_decode(sig_b64)
    except (ValueError, Exception):
        return None
    expected = hmac.new(config.SECRET.encode("utf-8"), raw, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        body = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None
    if int(body.get("exp") or 0) < int(time.time()):
        return None
    return body
