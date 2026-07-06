"""§0 ledger check — routes horizontal-change packs to the human ADR gate.

ADR-0017 makes the §0 horizontal-change ledger *machine-checked*: a pack loads on
the standard path only if its ledger equals ``"none, all additive"``. A pack
claiming any horizontal change (the falsifiability rule firing) is not silently
accepted or rejected — it is routed to a **human ADR gate**, refused until a
horizontal ADR raises the floor it needs. This turns the ADR-0016 falsifiability
rule from a review convention into an enforced control-flow branch.
"""

from __future__ import annotations

from dataclasses import dataclass

from .bundle import PackBundle

_ADDITIVE_LEDGER = "none, all additive"

ROUTE_STANDARD = "standard"
ROUTE_HUMAN_ADR_GATE = "human_adr_gate"


@dataclass(frozen=True)
class LedgerResult:
    ok: bool
    route: str
    reason: str = ""


def check_ledger(bundle: PackBundle) -> LedgerResult:
    normalized = bundle.ledger.strip().lower().rstrip(".")
    if normalized == _ADDITIVE_LEDGER:
        return LedgerResult(ok=True, route=ROUTE_STANDARD)
    return LedgerResult(
        ok=False,
        route=ROUTE_HUMAN_ADR_GATE,
        reason=(
            f"§0 ledger is '{bundle.ledger}', not '{_ADDITIVE_LEDGER}': a claimed "
            "horizontal change must pass a human ADR gate before loading"
        ),
    )
