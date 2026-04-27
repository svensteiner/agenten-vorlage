"""Output verification for automation runs."""

from dataclasses import dataclass, field
from typing import Any

import brain

from .context import ProjectContext


@dataclass
class VerificationResult:
    passed: bool
    score: int = 0
    feedback: list[str] = field(default_factory=list)
    improved_output: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Verifier:
    """Checks whether a result is good enough to trust or ship."""

    def verify(
        self,
        output: str,
        threshold: int = 7,
        *,
        task: str = "",
        step: str = "",
        context: ProjectContext | None = None,
    ) -> VerificationResult:
        if not output.strip():
            return VerificationResult(
                passed=False,
                score=0,
                feedback=["Empty output"],
            )
        if self._looks_like_error(output):
            return VerificationResult(
                passed=False,
                score=2,
                feedback=["Output looks like an error or blocked operation."],
                metadata={"mode": "heuristic"},
            )
        placeholder_feedback = self._placeholder_feedback(output)
        if placeholder_feedback:
            return VerificationResult(
                passed=False,
                score=4,
                feedback=placeholder_feedback,
                improved_output=self._remove_placeholder_lines(output),
                metadata={"mode": "heuristic", "reason": "placeholder"},
            )

        configured_threshold = threshold
        if context and context.config.get("quality_threshold"):
            try:
                configured_threshold = int(context.config["quality_threshold"])
            except (TypeError, ValueError):
                configured_threshold = threshold

        criteria = self._criteria(task=task, step=step, context=context)
        evaluation = brain.evaluate(output, content_type="agent_step_output", criteria=criteria)
        if evaluation and "score" in evaluation and "LLM nicht verf" not in " ".join(evaluation.get("feedback", [])):
            score = int(evaluation.get("score", 0))
            return VerificationResult(
                passed=bool(evaluation.get("passes", score >= configured_threshold)),
                score=score,
                feedback=[str(item) for item in evaluation.get("feedback", [])],
                improved_output=evaluation.get("improved_version"),
                metadata={"mode": "llm", "threshold": configured_threshold},
            )

        score = self._heuristic_score(output, task=task, step=step)
        return VerificationResult(
            passed=score >= configured_threshold,
            score=score,
            feedback=[f"Heuristic verification score: {score}/{configured_threshold}."],
            metadata={"mode": "heuristic", "threshold": configured_threshold},
        )

    def _criteria(self, *, task: str, step: str, context: ProjectContext | None) -> str:
        parts = [
            "The output must be relevant to the task and step.",
            "It must not contain unresolved tool errors.",
            "It must be concrete enough for the next agent step.",
            "It must not contain placeholders like '[fill in]' or invented facts.",
            "If evidence is incomplete, it should say what is missing instead of fabricating details.",
        ]
        if task:
            parts.append(f"Task: {task}")
        if step:
            parts.append(f"Step: {step}")
        if context and context.manifest.get("success_criteria"):
            parts.append(f"Project success criteria: {context.manifest['success_criteria']}")
        return "\n".join(parts)

    def _looks_like_error(self, output: str) -> bool:
        lowered = output.lower()
        markers = ["fehler", "error", "exception", "traceback", "blocked", "sicherheitsfehler"]
        return any(marker in lowered for marker in markers)

    def _placeholder_feedback(self, output: str) -> list[str]:
        lowered = output.lower()
        markers = [
            "[fill in]",
            "[missing",
            "tbd",
            "todo:",
            "lorem ipsum",
            "platzhalter",
        ]
        if any(marker in lowered for marker in markers):
            return ["Output contains placeholders or unresolved template text."]
        return []

    def _remove_placeholder_lines(self, output: str) -> str:
        markers = ["[fill in]", "[missing", "tbd", "todo:", "lorem ipsum", "platzhalter"]
        lines = []
        for line in output.splitlines():
            lowered = line.lower()
            if any(marker in lowered for marker in markers):
                continue
            lines.append(line)
        return "\n".join(lines).strip() or output

    def _heuristic_score(self, output: str, *, task: str, step: str) -> int:
        score = 6
        if len(output.strip()) >= 80:
            score += 1
        task_terms = {term for term in task.lower().split() if len(term) > 4}
        if task_terms and any(term in output.lower() for term in task_terms):
            score += 1
        if step and any(term in output.lower() for term in step.lower().split() if len(term) > 4):
            score += 1
        return min(score, 9)
