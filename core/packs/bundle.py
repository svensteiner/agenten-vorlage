"""Pack bundle — the signed, content-addressed, data-only artifact (RESOLVE stage).

A domain pack is distributed as a *bundle*: the machine-readable projection of
the six pack sections ([ADR-0016](platform/architecture/adr/ADR-0016-domain-pack-contract.md))
plus a §0 horizontal-change ledger. It carries **data + declarative config
only — no read-path code**. A connector is *referenced* by name, never shipped;
new connector code remains a platform PR through the connector gate. This keeps
"load a pack" down to "install validated config," never "run untrusted code on
the retrieval path" (ADR-0017).

Integrity has two independent controls:

* **content address** — ``content_hash`` == SHA-256 of the canonical section
  payload; any tampering with the sections breaks it; and
* **signature** — an HMAC over the content hash with the publisher key; a bundle
  whose sections were altered or which was signed by an unknown key is rejected
  at RESOLVE, before any validator runs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Any

# Dev/publisher signing key. In production this is a per-publisher key resolved
# from the trust store; kept as a module constant so the template runs offline
# and tests can mint valid bundles via ``make_bundle``.
_PUBLISHER_KEY = b"agenten-vorlage/pack-publisher/dev"


@dataclass(frozen=True)
class PackBundle:
    """Immutable, verified pack artifact. The six sections are data-only."""

    name: str
    version: str
    ledger: str  # §0 horizontal-change ledger
    acl_fixtures: tuple[dict[str, Any], ...] = ()   # §1
    labels: tuple[str, ...] = ()                     # §2 new labels
    matrix_deltas: dict[str, str] = field(default_factory=dict)  # §3 label→action
    compliance_rows: tuple[dict[str, Any], ...] = ()  # §4
    eval_models: tuple[str, ...] = ()                 # §5 referenced models
    agent_graph: tuple[str, ...] = ()                 # §6 handoff targets
    content_hash: str = ""
    signature: str = ""

    def sections(self) -> dict[str, Any]:
        """The canonical section payload the content hash is computed over."""
        return {
            "name": self.name,
            "version": self.version,
            "ledger": self.ledger,
            "acl_fixtures": list(self.acl_fixtures),
            "labels": list(self.labels),
            "matrix_deltas": dict(self.matrix_deltas),
            "compliance_rows": list(self.compliance_rows),
            "eval_models": list(self.eval_models),
            "agent_graph": list(self.agent_graph),
        }


class BundleError(ValueError):
    """Raised when a bundle fails integrity verification at RESOLVE."""


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_content_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def sign(content_hash: str, key: bytes = _PUBLISHER_KEY) -> str:
    return hmac.new(key, content_hash.encode("utf-8"), hashlib.sha256).hexdigest()


def make_bundle(
    *,
    name: str = "test-pack",
    version: str = "1.0.0",
    ledger: str = "none, all additive",
    acl_fixtures: tuple[dict[str, Any], ...] = (),
    labels: tuple[str, ...] = (),
    matrix_deltas: dict[str, str] | None = None,
    compliance_rows: tuple[dict[str, Any], ...] = (),
    eval_models: tuple[str, ...] = (),
    agent_graph: tuple[str, ...] = (),
    key: bytes = _PUBLISHER_KEY,
) -> PackBundle:
    """Mint a correctly-hashed, correctly-signed bundle (test + fixture helper)."""
    partial = PackBundle(
        name=name,
        version=version,
        ledger=ledger,
        acl_fixtures=acl_fixtures,
        labels=labels,
        matrix_deltas=dict(matrix_deltas or {}),
        compliance_rows=compliance_rows,
        eval_models=eval_models,
        agent_graph=agent_graph,
    )
    content_hash = compute_content_hash(partial.sections())
    signature = sign(content_hash, key)
    return PackBundle(
        name=name,
        version=version,
        ledger=ledger,
        acl_fixtures=acl_fixtures,
        labels=labels,
        matrix_deltas=dict(matrix_deltas or {}),
        compliance_rows=compliance_rows,
        eval_models=eval_models,
        agent_graph=agent_graph,
        content_hash=content_hash,
        signature=signature,
    )


def verify_bundle(bundle: PackBundle, *, key: bytes = _PUBLISHER_KEY) -> PackBundle:
    """RESOLVE: verify content address + signature. Raises BundleError on any mismatch."""
    expected_hash = compute_content_hash(bundle.sections())
    if not bundle.content_hash:
        raise BundleError("bundle has no content_hash")
    if not hmac.compare_digest(bundle.content_hash, expected_hash):
        raise BundleError(
            f"content-address mismatch: sections hash to {expected_hash[:12]}…, "
            f"bundle claims {bundle.content_hash[:12]}…"
        )
    expected_sig = sign(bundle.content_hash, key)
    if not bundle.signature or not hmac.compare_digest(bundle.signature, expected_sig):
        raise BundleError("signature invalid or signed by an unknown publisher key")
    return bundle


def load_bundle(data: dict[str, Any], *, key: bytes = _PUBLISHER_KEY) -> PackBundle:
    """Parse a raw dict into a verified PackBundle (RESOLVE)."""
    bundle = PackBundle(
        name=str(data.get("name", "")),
        version=str(data.get("version", "")),
        ledger=str(data.get("ledger", "")),
        acl_fixtures=tuple(data.get("acl_fixtures", ())),
        labels=tuple(data.get("labels", ())),
        matrix_deltas=dict(data.get("matrix_deltas", {})),
        compliance_rows=tuple(data.get("compliance_rows", ())),
        eval_models=tuple(data.get("eval_models", ())),
        agent_graph=tuple(data.get("agent_graph", ())),
        content_hash=str(data.get("content_hash", "")),
        signature=str(data.get("signature", "")),
    )
    return verify_bundle(bundle, key=key)
