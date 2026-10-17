"""Explicit, provider-preserving model escalation without transport retries."""
from __future__ import annotations

import hashlib
import json
import urllib.parse

from .contracts import ContractError
from .engine import Backend


def _normalize_endpoint_url(raw: object) -> str:
    if not isinstance(raw, str):
        raise ContractError("Routed provider endpoint identity must be text.")
    try:
        parsed = urllib.parse.urlsplit(raw.strip())
        port = parsed.port
    except ValueError as exc:
        raise ContractError("Routed provider endpoint identity is invalid.") from exc
    if (parsed.scheme.lower() != "https" or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or "?" in raw or "#" in raw):
        raise ContractError("Routed provider endpoints must be credential-free HTTPS URLs.")
    host = parsed.hostname.encode("idna").decode("ascii").lower()
    authority = f"[{host}]" if ":" in host else host
    if port not in (None, 443):
        authority += f":{port}"
    path = parsed.path.rstrip("/")
    return f"https://{authority}{path}"


def _endpoint_identity(backend: Backend) -> str | None:
    """Return a nonsecret endpoint identity and verify it matches transport config."""
    claimed = getattr(backend, "endpoint_identity", None)
    transport = getattr(backend, "base_url", None)
    if claimed is None and transport is None:
        return None
    normalized_claim = _normalize_endpoint_url(claimed) if claimed is not None else None
    normalized_transport = _normalize_endpoint_url(transport) if transport is not None else None
    if (normalized_claim is not None and normalized_transport is not None
            and normalized_claim != normalized_transport):
        raise ContractError("Claimed provider endpoint does not match the transport URL.")
    return normalized_transport if normalized_transport is not None else normalized_claim


class EscalatingBackend:
    """Route one assignment; the Engine still owns budgets, approvals and review."""

    def __init__(self, primary: Backend, *, recovery: Backend | None = None,
                 reviewer: Backend | None = None, repair_after: int = 2):
        if type(repair_after) is not int or not 1 <= repair_after <= 10:
            raise ContractError("repair_after must be an integer between 1 and 10.")
        backends = [backend for backend in (primary, recovery, reviewer) if backend is not None]
        if any(backend.name != primary.name for backend in backends):
            raise ContractError("Model routing must preserve the configured provider/backend.")
        endpoints = tuple(_endpoint_identity(backend) for backend in backends)
        if any(endpoint != endpoints[0] for endpoint in endpoints[1:]):
            raise ContractError("Model routing must preserve the configured provider endpoint.")
        self.primary, self.recovery, self.reviewer = primary, recovery, reviewer
        self._configured_backends = tuple(backends)
        self._endpoint_identities = endpoints
        self._backend_names = tuple(backend.name for backend in backends)
        self.repair_after = repair_after
        self.name = primary.name
        self.model = getattr(primary, "model", None)
        self.supports_action_approvals = all(
            getattr(backend, "supports_action_approvals", False) for backend in backends)
        # Engine checks this before planning or dispatching. A wrapper may advertise
        # strict enforcement only when every backend it can select enforces it.
        self.supports_write_policy = all(
            getattr(backend, "supports_write_policy", False) is True for backend in backends)

    @property
    def approval_identity(self) -> str:
        self._assert_provider_identity()
        policy = {"version": 1, "backend": self.name, "repair_after": self.repair_after,
                  "models": [getattr(backend, "model", None) if backend is not None else None
                             for backend in (self.primary, self.recovery, self.reviewer)],
                  "endpoint": self._endpoint_identities[0] if self._endpoint_identities else None}
        # A pending approval covers the whole routing configuration.
        # Changing a recovery/review model must invalidate it, even if primary stays.
        return "routing-v1:" + hashlib.sha256(
            json.dumps(policy, sort_keys=True).encode("utf-8")).hexdigest()

    def _assert_provider_identity(self) -> None:
        current_names = tuple(backend.name for backend in self._configured_backends)
        current_endpoints = tuple(_endpoint_identity(backend) for backend in self._configured_backends)
        if current_names != self._backend_names or current_endpoints != self._endpoint_identities:
            raise ContractError("A routed provider identity changed after routing was configured.")

    @staticmethod
    def _revisions(context: dict) -> int:
        roles = context["catalog"]["roles"]
        revisions = 0
        for record in context.get("history", []):
            report = record.get("report", {})
            role = roles.get(record.get("decision", {}).get("role"), {})
            if (report.get("status") == "success" and role.get("can_review")
                    and report.get("evidence")):
                revisions = 0
            elif report.get("status") == "needs_revision":
                revisions += 1
        return revisions

    def _select(self, decision: dict, context: dict) -> tuple[Backend, str]:
        if context["catalog"]["roles"][decision["role"]]["can_review"] and self.reviewer is not None:
            return self.reviewer, "independent_review"
        if self.recovery is not None and self._revisions(context) >= self.repair_after:
            return self.recovery, "repeated_revision"
        return self.primary, "primary"

    def execution_route(self, decision: dict, context: dict) -> dict:
        backend, reason = self._select(decision, context)
        return {"backend": backend.name, "model": getattr(backend, "model", None),
                "reason": reason, "revisions": self._revisions(context)}

    def decide(self, context: dict, timeout: float) -> dict:
        self._assert_provider_identity()
        return self.primary.decide(context, timeout)

    def execute(self, decision: dict, context: dict, timeout: float) -> dict:
        self._assert_provider_identity()
        backend, _ = self._select(decision, context)
        # Never catch/retry an interrupted tool or unknown provider outcome.
        return backend.execute(decision, context, timeout)
