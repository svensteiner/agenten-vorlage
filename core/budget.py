"""Fail-closed rental metering for a single agent run.

Inspired by langgraph-agent-stack cost caps; implemented here without that
dependency. Zero or None on a dimension means that dimension is unlimited.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any


def _as_decimal(value: Decimal | int | float | str | None) -> Decimal:
    """Parse a money amount with deterministic Decimal math (no float leftovers)."""
    if value is None:
        return Decimal("0")
    if isinstance(value, bool):
        raise ValueError("boolean is not a money amount")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("money amount must be finite")
        return value
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("money amount must be a finite decimal") from exc
    if not parsed.is_finite():
        raise ValueError("money amount must be finite")
    return parsed


def _as_token_count(value: int | str | None) -> int:
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int):
        try:
            parsed = int(str(value).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError("token count must be an integer") from exc
        if str(parsed) != str(value).strip():
            raise ValueError("token count must be an integer")
        value = parsed
    if value < 0:
        raise ValueError("token count cannot be negative")
    return value


@dataclass
class BudgetCheck:
    allowed: bool
    reason: str = ""


@dataclass
class RunBudget:
    """Per-run spend cap. Exceeding either configured cap is not allowed."""

    max_usd: Decimal | None = None
    max_tokens: int | None = None
    spent_usd: Decimal = field(default_factory=lambda: Decimal("0"))
    spent_tokens: int = 0

    @classmethod
    def from_config(cls, config: dict[str, Any] | None) -> RunBudget | None:
        """Return a budget when `run_budget` is present; otherwise unlimited (None)."""
        if not isinstance(config, dict):
            return None
        raw = config.get("run_budget")
        if not isinstance(raw, dict):
            return None
        max_usd = cls._optional_cap_usd(raw.get("max_usd"))
        max_tokens = cls._optional_cap_tokens(raw.get("max_tokens"))
        return cls(max_usd=max_usd, max_tokens=max_tokens)

    @staticmethod
    def _optional_cap_usd(value: Any) -> Decimal | None:
        if value is None:
            return None
        amount = _as_decimal(value)
        if amount < 0:
            raise ValueError("max_usd cannot be negative")
        # Zero means "this dimension is unlimited".
        return None if amount == 0 else amount

    @staticmethod
    def _optional_cap_tokens(value: Any) -> int | None:
        if value is None:
            return None
        count = _as_token_count(value)
        return None if count == 0 else count

    def _unlimited_usd(self) -> bool:
        return self.max_usd is None

    def _unlimited_tokens(self) -> bool:
        return self.max_tokens is None

    def charge(self, tokens: int = 0, usd: Decimal | int | float | str = 0) -> None:
        """Add spend. Token and USD dimensions are independent."""
        self.spent_tokens += _as_token_count(tokens)
        self.spent_usd += _as_decimal(usd)

    def remaining(self) -> dict[str, Decimal | int | None]:
        usd: Decimal | None
        tokens: int | None
        if self._unlimited_usd():
            usd = None
        else:
            assert self.max_usd is not None
            usd = self.max_usd - self.spent_usd
        if self._unlimited_tokens():
            tokens = None
        else:
            assert self.max_tokens is not None
            tokens = self.max_tokens - self.spent_tokens
        return {"usd": usd, "tokens": tokens}

    def check(self) -> BudgetCheck:
        """Fail closed when remaining would be negative on a capped dimension."""
        leftover = self.remaining()
        usd_left = leftover["usd"]
        tokens_left = leftover["tokens"]
        if usd_left is not None and usd_left < 0:
            return BudgetCheck(
                allowed=False,
                reason="402 budget_exceeded: USD cap exceeded",
            )
        if tokens_left is not None and tokens_left < 0:
            return BudgetCheck(
                allowed=False,
                reason="402 budget_exceeded: token cap exceeded",
            )
        return BudgetCheck(allowed=True, reason="")

    @property
    def exceeded(self) -> bool:
        return not self.check().allowed

    @property
    def deny_reason(self) -> str:
        return self.check().reason


def spent_from_metadata(metadata: dict[str, Any] | None) -> tuple[Decimal, int]:
    """Read `usd`/`tokens` (or spent_*) from plan/step metadata."""
    if not isinstance(metadata, dict):
        return Decimal("0"), 0
    usd_raw = metadata.get("usd", metadata.get("spent_usd"))
    token_raw = metadata.get("tokens", metadata.get("spent_tokens"))
    usd = Decimal("0") if usd_raw is None else _as_decimal(usd_raw)
    tokens = 0 if token_raw is None else _as_token_count(token_raw)
    return usd, tokens


def plan_spend(plan: Any) -> tuple[Decimal, int]:
    """Sum usd/tokens advertised on the plan and its steps (fail closed)."""
    total_usd = Decimal("0")
    total_tokens = 0
    plan_meta = getattr(plan, "metadata", None)
    usd, tokens = spent_from_metadata(plan_meta if isinstance(plan_meta, dict) else None)
    total_usd += usd
    total_tokens += tokens
    steps = getattr(plan, "steps", None) or []
    for step in steps:
        usd, tokens = spent_from_metadata(getattr(step, "metadata", None))
        total_usd += usd
        total_tokens += tokens
    return total_usd, total_tokens


def evaluate_run_budget(
    config: dict[str, Any] | None,
    *,
    spent_usd: Decimal | int | float | str | None = None,
    spent_tokens: int | None = None,
) -> BudgetCheck | None:
    """None means no `run_budget` configured (current unlimited behaviour)."""
    try:
        budget = RunBudget.from_config(config)
    except ValueError as exc:
        return BudgetCheck(allowed=False, reason=f"402 budget_exceeded: invalid run_budget ({exc})")
    if budget is None:
        return None
    budget.charge(tokens=spent_tokens or 0, usd=spent_usd or 0)
    return budget.check()
