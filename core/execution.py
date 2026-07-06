"""ExecutionBackend port — the execution plane (ADR-0019 §4.4).

The distributed orchestrator is split into two planes:

* a **decision plane** (ours, in-boundary) — planning, governance, tool scope,
  handoff routing, and the single verifier answer gate; and
* an **execution plane** — durable state, retries, timers, fan-out, resume.

This module is the *execution plane* seam. The ``ExecutionBackend`` Protocol
carries **no decision method**: it cannot plan, pick a tool, call a model, emit
an answer, verify, or allow. It only schedules opaque *activities* and awaits
their results. That absence is the whole point — it is what lets a commodity
durable-execution substrate be adopted behind the port without ever becoming a
competing choke point (mirroring the ``VectorIndex`` port's missing
unfiltered-search method).

The invariant is machine-checked: ``DECISION_VERBS`` names every verb that must
*not* appear on the port, and ``test_execution_port.py`` asserts the Protocol's
method set is disjoint from it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, Sequence, runtime_checkable

# Verbs that would turn the execution plane into a decision maker. The port must
# expose none of these — enforced by test_execution_port.py as a grep-invariant.
DECISION_VERBS: frozenset[str] = frozenset(
    {"plan", "select_tool", "call_model", "answer", "verify", "allow", "route"}
)


@dataclass(frozen=True)
class Step:
    """An opaque unit of work handed to the execution plane.

    ``activity`` is a caller-supplied callable that performs the actual work. The
    backend never inspects it — from the port's perspective it is an opaque
    activity reference (a distributed adapter would carry a serializable handle
    instead of a live callable). This is how the *what* stays in the decision
    plane while the *when/whether/retry* moves to the execution plane.
    """

    id: str
    activity: Callable[[], "StepResult"]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StepResult:
    id: str
    output: str = ""
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunSpec:
    tenant_id: str
    request_id: str

    @property
    def run_id(self) -> str:
        return f"{self.tenant_id}:{self.request_id}"


@dataclass
class RunHandle:
    run_id: str
    tenant_id: str
    steps: list["StepHandle"] = field(default_factory=list)


@dataclass
class StepHandle:
    run_id: str
    step_id: str


@runtime_checkable
class ExecutionBackend(Protocol):
    """Durable-execution port. No method here makes a decision — by construction.

    A distributed adapter (Temporal-class) implements the same Protocol; swapping
    it in is a second adapter, never a caller change.
    """

    def start_run(self, run_spec: RunSpec, *, idempotency_key: str) -> RunHandle: ...

    def schedule_step(self, run: RunHandle, step: Step, *, idempotency_key: str) -> StepHandle: ...

    def await_steps(self, run: RunHandle, steps: Sequence[StepHandle]) -> list[StepResult]: ...

    def signal(self, run: RunHandle, name: str, payload: dict) -> None: ...

    def timer(self, run: RunHandle, seconds: float) -> None: ...

    def resume(self, run_id: str) -> RunHandle: ...


class InProcessExecutionBackend:
    """Default synchronous, dict-backed adapter.

    ``schedule_step`` records the activity; ``await_steps`` runs each recorded
    activity immediately and returns its result. Behaviour is identical to a
    straight-line ``for`` loop, so re-expressing the orchestrator against this
    port changes no observable output — proving the port is a faithful seam. It
    stays forever as the unit-test and small-Isolated-tenant backend; the
    distributed adapter is purely additive.
    """

    def __init__(self) -> None:
        self._runs: dict[str, RunHandle] = {}
        self._activities: dict[tuple[str, str], Step] = {}
        self._results: dict[tuple[str, str], StepResult] = {}
        self._committed: set[str] = set()

    def start_run(self, run_spec: RunSpec, *, idempotency_key: str) -> RunHandle:
        existing = self._runs.get(run_spec.run_id)
        if existing is not None:
            # Idempotent: starting the same run twice returns the same handle.
            return existing
        handle = RunHandle(run_id=run_spec.run_id, tenant_id=run_spec.tenant_id)
        self._runs[run_spec.run_id] = handle
        return handle

    def schedule_step(self, run: RunHandle, step: Step, *, idempotency_key: str) -> StepHandle:
        key = (run.run_id, step.id)
        self._activities[key] = step
        handle = StepHandle(run_id=run.run_id, step_id=step.id)
        run.steps.append(handle)
        return handle

    def await_steps(self, run: RunHandle, steps: Sequence[StepHandle]) -> list[StepResult]:
        results: list[StepResult] = []
        for sh in steps:
            key = (sh.run_id, sh.step_id)
            cached = self._results.get(key)
            if cached is None:
                step = self._activities[key]
                cached = step.activity()
                self._results[key] = cached
            results.append(cached)
        return results

    def signal(self, run: RunHandle, name: str, payload: dict) -> None:
        # No-op in-process: signals matter only for the distributed adapter.
        return None

    def timer(self, run: RunHandle, seconds: float) -> None:
        # No-op in-process: durable timers matter only for the distributed adapter.
        return None

    def resume(self, run_id: str) -> RunHandle:
        handle = self._runs.get(run_id)
        if handle is None:
            raise KeyError(f"unknown run_id: {run_id}")
        return handle
