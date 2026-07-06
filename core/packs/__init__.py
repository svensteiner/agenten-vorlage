"""core.packs — runtime pack-load SPI (ADR-0017).

The engineering form of the [domain-pack contract](platform/architecture/adr/ADR-0016-domain-pack-contract.md):
a validating, transactional, fail-closed loader that installs a signed, data-only
pack bundle into its horizontal extension points and **structurally rejects any
floor-loosening pack** — by code, not by review.

Pipeline: RESOLVE (``bundle``) → VALIDATE (``validators`` + ``ledger``) →
DRY-RUN (``dryrun``) → COMMIT-atomic (``loader``) → ACTIVATE-scoped (``activation``).
"""

from .activation import ActivationRegistry, UnloadRefused
from .bundle import BundleError, PackBundle, load_bundle, make_bundle, verify_bundle
from .dryrun import InstallPlan, plan_install
from .ledger import LedgerResult, check_ledger
from .loader import ExtensionStore, Loader, LoadResult
from .validators import ExtensionPoints, ValidationResult, validate_bundle

__all__ = [
    "ActivationRegistry",
    "UnloadRefused",
    "BundleError",
    "PackBundle",
    "load_bundle",
    "make_bundle",
    "verify_bundle",
    "InstallPlan",
    "plan_install",
    "LedgerResult",
    "check_ledger",
    "ExtensionStore",
    "Loader",
    "LoadResult",
    "ExtensionPoints",
    "ValidationResult",
    "validate_bundle",
]
