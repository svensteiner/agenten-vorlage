"""Deterministic input/output guardrails (OpenAI Agents SDK idea, our functions).

No LLM-as-judge. Tripwires fail closed when wired into governance / verifier.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class GuardrailResult:
    tripwire: bool
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"tripwire": self.tripwire, "reason": self.reason}


_INVENT_BOOKING = re.compile(
    r"(?:erfinde|erfinden|ausdenken|fiktiv(?:e|en)?|invent(?:ed|ing)?|fabricat(?:e|ed|ing)?)"
    r".{0,80}"
    r"(?:buchung(?:en)?|bookings?)",
    re.IGNORECASE | re.DOTALL,
)
_INVENT_BOOKING_REV = re.compile(
    r"(?:buchung(?:en)?|bookings?)"
    r".{0,80}"
    r"(?:erfinde|erfinden|ausdenken|fiktiv|invent|fabricat|ohne\s+(?:quelle|beleg|source)|without\s+source)",
    re.IGNORECASE | re.DOTALL,
)
_BOOKING_WITHOUT_SOURCE = re.compile(
    r"(?:buchung(?:en)?|bookings?).{0,80}(?:ohne\s+(?:quelle|beleg|source)|without\s+(?:a\s+)?source|no source)",
    re.IGNORECASE | re.DOTALL,
)
_PII_DUMP = re.compile(
    r"(?:dump|exfiltr|exportiere|gib\s+alle|zeige\s+alle|leak).{0,60}"
    r"(?:iban|pii|personen(?:daten)?|kundendaten|sozialversicher)",
    re.IGNORECASE | re.DOTALL,
)
_PII_DUMP_REV = re.compile(
    r"(?:iban|pii|personen(?:daten)?|kundendaten).{0,60}"
    r"(?:dump|exfiltr|exportiere|gib\s+alle|zeige\s+alle|leak)",
    re.IGNORECASE | re.DOTALL,
)
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
_AMOUNT = re.compile(
    r"(?:€|\bEUR\b|\bUSD\b)|"
    r"\b(?:ebitda|umsatz|revenue_month|egt_month)\b|"
    r"-?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?\s*€?",
    re.IGNORECASE,
)
_SUCCESS_CLAIM = re.compile(
    r"\b(?:erfolgreich(?:er)?|successfully|success\b|\"passed\"\s*:\s*true|\"success\"\s*:\s*true)\b",
    re.IGNORECASE,
)
_SOURCE_KEYS = (
    "source",
    "citations",
    "reconciliation",
    "evidence",
    "quelle",
    "beleg",
    "source_file",
)
_NEGATED_SOURCE = re.compile(
    r"(?:ohne|without|no|kein(?:e|en)?)\s+(?:\w+\s+){0,4}"
    r"(?:quelle|quellen|beleg|belege|source|sources|citation|citations|evidence)",
    re.IGNORECASE,
)


def _has_source_evidence(text: str) -> bool:
    lowered = text.lower()
    if _NEGATED_SOURCE.search(lowered):
        return False
    return any(
        re.search(r"\b" + re.escape(key) + r"\b", lowered) for key in _SOURCE_KEYS
    )


def check_input_guardrail(text: str) -> GuardrailResult:
    """Block invented bookings without source and obvious PII-dump instructions."""
    blob = text or ""
    if not blob.strip():
        return GuardrailResult(tripwire=False)
    if (
        _INVENT_BOOKING.search(blob)
        or _INVENT_BOOKING_REV.search(blob)
        or _BOOKING_WITHOUT_SOURCE.search(blob)
    ):
        return GuardrailResult(
            tripwire=True,
            reason="input_guardrail: inventing Buchungen/bookings without a source is blocked",
        )
    if _PII_DUMP.search(blob) or _PII_DUMP_REV.search(blob):
        return GuardrailResult(
            tripwire=True,
            reason="input_guardrail: PII dump instruction is blocked",
        )
    if _IBAN.search(blob) and re.search(
        r"\b(?:dump|exfiltr|exportiere|gib alle|zeige alle|leak)\b", blob, re.I
    ):
        return GuardrailResult(
            tripwire=True,
            reason="input_guardrail: IBAN/PII dump instruction is blocked",
        )
    return GuardrailResult(tripwire=False)


def check_output_guardrail(output: str) -> GuardrailResult:
    """Trip if amounts or success claims ship without source/evidence keys."""
    blob = output or ""
    if not blob.strip():
        return GuardrailResult(tripwire=False)
    has_source = _has_source_evidence(blob)
    if _AMOUNT.search(blob) and not has_source:
        return GuardrailResult(
            tripwire=True,
            reason="output_guardrail: amounts present without source/evidence keys",
        )
    if _SUCCESS_CLAIM.search(blob) and not has_source:
        return GuardrailResult(
            tripwire=True,
            reason="output_guardrail: success claimed while sources are missing",
        )
    return GuardrailResult(tripwire=False)


class InputGuardrail:
    """Callable wrapper matching the Agents-SDK tripwire shape."""

    def check(self, text: str) -> dict[str, Any]:
        return check_input_guardrail(text).as_dict()


class OutputGuardrail:
    def check(self, output: str) -> dict[str, Any]:
        return check_output_guardrail(output).as_dict()