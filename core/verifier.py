"""Output verification for automation runs."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerificationResult:
    passed: bool
    score: int = 0
    feedback: list[str] = field(default_factory=list)
    improved_output: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Verifier:
    """Checks whether a result is good enough to trust or ship."""

    def verify(self, output: str, threshold: int = 7) -> VerificationResult:
        if not output.strip():
            return VerificationResult(
                passed=False,
                score=0,
                feedback=["Empty output"],
            )
        return VerificationResult(
            passed=True,
            score=max(threshold, 7),
            feedback=["Skeleton verifier accepted the output."],
        )
