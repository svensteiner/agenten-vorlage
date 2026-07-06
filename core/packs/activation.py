"""ACTIVATE — tenant-scoped activation, version pinning, fail-closed unload (ADR-0017).

Activation is the final stage: a committed pack is switched on **per tenant**, at
a **pinned version** (reusing the model-version pinning pattern). Unload is
**fail-closed**: a pack whose label is still *live* (in use by indexed content or
a policy) cannot remove that label, because removing a live label would silently
widen access on everything still classified by it. A wrong unload therefore costs
availability, never safety.
"""

from __future__ import annotations

from dataclasses import dataclass


class UnloadRefused(RuntimeError):
    """Raised when a fail-closed unload is blocked by a live label."""


@dataclass
class _Activation:
    pack: str
    version: str
    labels: frozenset[str]


class ActivationRegistry:
    """Per-tenant pack activation state with fail-closed unload."""

    def __init__(self) -> None:
        self._active: dict[tuple[str, str], _Activation] = {}
        self._live_labels: dict[str, set[str]] = {}  # tenant → labels currently in use

    # ── Activation / pinning ─────────────────────────────────────────────────

    def activate(self, tenant: str, pack: str, version: str, *, labels: tuple[str, ...] = ()) -> None:
        self._active[(tenant, pack)] = _Activation(pack=pack, version=version, labels=frozenset(labels))

    def active_version(self, tenant: str, pack: str) -> str | None:
        act = self._active.get((tenant, pack))
        return act.version if act else None

    def is_active(self, tenant: str, pack: str) -> bool:
        return (tenant, pack) in self._active

    def pin(self, tenant: str, pack: str, version: str) -> None:
        """Pin a tenant to a specific pack version (rollback = pin to prior)."""
        act = self._active.get((tenant, pack))
        if act is None:
            raise KeyError(f"pack '{pack}' not active for tenant '{tenant}'")
        self._active[(tenant, pack)] = _Activation(pack=pack, version=version, labels=act.labels)

    # ── Live-label tracking (what makes unload fail-closed) ───────────────────

    def mark_label_live(self, tenant: str, label: str) -> None:
        self._live_labels.setdefault(tenant, set()).add(label)

    def clear_label(self, tenant: str, label: str) -> None:
        self._live_labels.get(tenant, set()).discard(label)

    def live_labels(self, tenant: str, pack: str) -> frozenset[str]:
        act = self._active.get((tenant, pack))
        if act is None:
            return frozenset()
        return frozenset(act.labels & self._live_labels.get(tenant, set()))

    # ── Fail-closed unload ────────────────────────────────────────────────────

    def unload(self, tenant: str, pack: str) -> None:
        """Deactivate a pack — refused while any of its labels is still live."""
        blocking = self.live_labels(tenant, pack)
        if blocking:
            raise UnloadRefused(
                f"cannot unload pack '{pack}' for tenant '{tenant}': "
                f"label(s) still live: {sorted(blocking)}"
            )
        self._active.pop((tenant, pack), None)
