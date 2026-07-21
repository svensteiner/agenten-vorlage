"""Output verification for automation runs."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import json
import re
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

        missing_data = self._verify_controlling_missing_data(
            output,
            task=task,
            context=context,
            threshold=configured_threshold,
        )
        if missing_data is not None:
            return missing_data

        deterministic = self._verify_controlling_evidence(
            output,
            context=context,
            threshold=configured_threshold,
        )
        if deterministic is not None:
            return deterministic

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

    def _verify_controlling_missing_data(
        self,
        output: str,
        *,
        task: str,
        context: ProjectContext | None,
        threshold: int,
    ) -> VerificationResult | None:
        """Verify the scheduler's deterministic stop/wait contract locally."""
        manifest = context.manifest if context else {}
        workflow = manifest.get("workflow", {}) if isinstance(manifest, dict) else {}
        if not isinstance(workflow, dict) or workflow.get("name") != "kmu-controlling":
            return None

        signal = None
        for line in task.splitlines():
            if not line.startswith("SCHEDULER_SIGNAL:"):
                continue
            try:
                candidate = json.loads(line.removeprefix("SCHEDULER_SIGNAL:").strip())
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                signal = candidate
        if (
            signal is None
            or signal.get("reason") != "missing_data"
            or signal.get("reasons") != ["missing_data"]
            or not re.fullmatch(
                r"schedule-[0-9a-f]{20}", str(signal.get("event_id", ""))
            )
        ):
            return None

        raw_groups = signal.get("missing_required_groups")
        if not isinstance(raw_groups, list) or not raw_groups:
            return None
        group_ids: list[str] = []
        for group in raw_groups:
            if not isinstance(group, dict):
                return None
            group_id, count, minimum = (
                group.get("id"),
                group.get("count"),
                group.get("minimum"),
            )
            if (
                not isinstance(group_id, str)
                or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", group_id)
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count < 0
                or isinstance(minimum, bool)
                or not isinstance(minimum, int)
                or minimum <= 0
                or count >= minimum
            ):
                return None
            group_ids.append(group_id)

        lowered = output.lower()
        required_text = (
            "scheduled status missing_data",
            "kpi computation and external actions remain paused",
            "wait for the required inputs",
        )
        if not all(text in lowered for text in required_text) or not all(
            group_id in output for group_id in group_ids
        ):
            return None
        score = 10
        return VerificationResult(
            passed=score >= threshold,
            score=score,
            feedback=["Missing inputs are named; KPI and external actions are paused."],
            metadata={"mode": "deterministic_missing_data", "threshold": threshold},
        )

    def _verify_controlling_evidence(
        self,
        output: str,
        *,
        context: ProjectContext | None,
        threshold: int,
    ) -> VerificationResult | None:
        """Accept a complete source-backed pilot report without another LLM call."""
        manifest = context.manifest if context else {}
        workflow = manifest.get("workflow", {}) if isinstance(manifest, dict) else {}
        if not isinstance(workflow, dict) or workflow.get("name") != "kmu-controlling":
            return None

        objects: list[dict[str, Any]] = []
        for line in output.splitlines():
            try:
                value = json.loads(line.strip())
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(value, dict):
                objects.append(value)

        computations = [
            value
            for value in objects
            if isinstance(value.get("metrics"), dict)
            and isinstance(value.get("reconciliation"), dict)
            and isinstance(value.get("source"), str)
            and isinstance(value.get("method"), str)
        ]
        drafts = [
            value
            for value in objects
            if value.get("mode") in {"deterministic_fallback", "model_draft"}
        ]
        for computation in computations:
            if not self._valid_controlling_computation(computation):
                continue
            for draft in drafts:
                if not self._valid_controlling_draft(draft, computation):
                    continue
                score = 10
                return VerificationResult(
                    passed=score >= threshold,
                    score=score,
                    feedback=[
                        "Deterministic KPIs, reconciliation, management contract, "
                        "and citations are internally consistent."
                    ],
                    metadata={
                        "mode": "deterministic_controlling",
                        "threshold": threshold,
                    },
                )
        return None

    @classmethod
    def _valid_controlling_computation(cls, value: dict[str, Any]) -> bool:
        reconciliation = value["reconciliation"]
        counts = []
        for name in (
            "source_account_count",
            "mapped_account_count",
            "ignored_account_count",
        ):
            count = reconciliation.get(name)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                return False
            counts.append(count)
        if counts[0] == 0 or counts[0] != counts[1] + counts[2]:
            return False
        if not value["source"].strip() or not value["method"].strip():
            return False
        metrics = value["metrics"]
        for name in ("ebitda", "depreciation", "egt"):
            metric = metrics.get(name)
            if not isinstance(metric, dict) or not all(
                cls._finite_number(metric.get(period))
                for period in ("month", "prior", "ytd", "ytd_prior")
            ):
                return False
        provenance = value.get("provenance")
        if (
            not isinstance(provenance, dict)
            or set(provenance)
            != {"input_fingerprint", "mapping_version", "calculation_version"}
            or provenance.get("calculation_version") != "kmu-report-v1"
            or not all(
                isinstance(provenance.get(name), str)
                and re.fullmatch(r"[0-9a-f]{64}", provenance[name])
                for name in ("input_fingerprint", "mapping_version")
            )
        ):
            return False
        return True

    @staticmethod
    def _finite_number(value: Any) -> bool:
        if value is None or isinstance(value, bool):
            return False
        try:
            return Decimal(str(value)).is_finite()
        except InvalidOperation:
            return False

    @staticmethod
    def _valid_controlling_draft(
        draft: dict[str, Any], computation: dict[str, Any]
    ) -> bool:
        summary = draft.get("summary")
        alarms = draft.get("alarms")
        actions = draft.get("actions")
        citations = draft.get("citations")
        if (
            not isinstance(summary, str)
            or len(re.findall(r"[.!?](?:\s|$)", summary.strip())) != 3
            or not isinstance(alarms, list)
            or len(alarms) > 4
            or not all(isinstance(item, str) for item in alarms)
            or not isinstance(actions, list)
            or len(actions) != 3
            or not all(isinstance(item, str) for item in actions)
            or not isinstance(citations, dict)
        ):
            return False
        return citations == {
            "source": computation["source"],
            "method": computation["method"],
        }

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
