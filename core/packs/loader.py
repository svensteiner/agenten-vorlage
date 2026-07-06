"""Pack loader — the staged, transactional, fail-closed pipeline (ADR-0017).

    RESOLVE → VALIDATE → DRY-RUN → COMMIT(atomic) → ACTIVATE(tenant-scoped)

Two properties define this loader and both are proven by unit tests, not review:

1. **A floor-loosening bundle is rejected structurally.** VALIDATE runs the six
   subset validators; a bundle that loosens any floor fails with a named
   ``rejected_by`` — ADR-0017's headline claim, machine-checked
   (``test_pack_validate.py::test_floor_loosening_bundle_fails_validate``).
2. **Partial installation is unrepresentable.** COMMIT applies all six sections
   to a staged copy and swaps atomically; any failure — a validator injected
   mid-VALIDATE, or a section write raising mid-COMMIT — leaves *zero* sections
   installed. Partial install is the one state that could transiently loosen a
   floor, so it is made impossible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .bundle import BundleError, PackBundle, verify_bundle
from .dryrun import InstallPlan, plan_install
from .ledger import ROUTE_HUMAN_ADR_GATE, check_ledger
from .validators import ExtensionPoints, validate_bundle

# Pipeline stages, in order — reported in LoadResult.stage on failure.
STAGE_RESOLVE = "RESOLVE"
STAGE_VALIDATE = "VALIDATE"
STAGE_DRYRUN = "DRY-RUN"
STAGE_COMMIT = "COMMIT"
STAGE_DONE = "DONE"


class ExtensionStore:
    """The stores a pack installs into. Commits are all-or-nothing.

    ``install_hook`` lets a test inject a COMMIT-phase failure at a named section
    to prove atomicity (the staged copy is discarded, nothing persists).
    """

    def __init__(self, install_hook=None) -> None:
        self._sections: dict[str, Any] = {}
        self._install_hook = install_hook

    def installed_sections(self) -> tuple[str, ...]:
        return tuple(sorted(self._sections))

    def get(self, section: str) -> Any:
        return self._sections.get(section)

    def commit(self, writes: dict[str, Any]) -> None:
        """Atomically apply all writes, or none. Never a partial state."""
        staged = dict(self._sections)  # work on a copy
        for section, payload in writes.items():
            if self._install_hook is not None:
                self._install_hook(section, payload)  # may raise → abort, nothing swapped
            staged[section] = payload
        self._sections = staged  # single atomic swap on full success


@dataclass(frozen=True)
class LoadResult:
    ok: bool
    stage: str = STAGE_DONE
    rejected_by: str = ""
    route: str = ""
    reason: str = ""
    plan: InstallPlan | None = None
    installed: tuple[str, ...] = field(default_factory=tuple)


class Loader:
    """Drives one bundle through the five-stage pipeline against a store."""

    def __init__(self, store: ExtensionStore | None = None, ext: ExtensionPoints | None = None) -> None:
        self.store = store or ExtensionStore()
        self.ext = ext or ExtensionPoints()

    def validate(self, bundle: PackBundle, *, fail_validator: str | None = None):
        """Expose VALIDATE directly (the marquee falsifiability test calls this)."""
        return validate_bundle(bundle, self.ext, fail_validator=fail_validator)

    def load(self, bundle: PackBundle, *, fail_validator: str | None = None) -> LoadResult:
        # ── RESOLVE — verify integrity before anything else touches the bundle ──
        try:
            verify_bundle(bundle)
        except BundleError as exc:
            return LoadResult(ok=False, stage=STAGE_RESOLVE, reason=str(exc))

        # ── VALIDATE — §0 ledger (route horizontal packs out) then six checks ──
        led = check_ledger(bundle)
        if not led.ok:
            return LoadResult(
                ok=False,
                stage=STAGE_VALIDATE,
                route=ROUTE_HUMAN_ADR_GATE,
                reason=led.reason,
            )
        result = self.validate(bundle, fail_validator=fail_validator)
        if not result.ok:
            return LoadResult(
                ok=False,
                stage=STAGE_VALIDATE,
                rejected_by=result.rejected_by,
                reason="; ".join(result.reasons),
                installed=self.store.installed_sections(),
            )

        # ── DRY-RUN — compute the install plan (no mutation) ───────────────────
        plan = plan_install(bundle)

        # ── COMMIT — atomic, all-or-nothing ────────────────────────────────────
        writes = {section: summary for section, summary in plan.writes}
        try:
            self.store.commit(writes)
        except Exception as exc:  # a section write failed → nothing persisted
            return LoadResult(
                ok=False,
                stage=STAGE_COMMIT,
                reason=f"commit failed, rolled back: {exc}",
                plan=plan,
                installed=self.store.installed_sections(),
            )

        return LoadResult(
            ok=True,
            stage=STAGE_DONE,
            route=led.route,
            plan=plan,
            installed=self.store.installed_sections(),
        )
