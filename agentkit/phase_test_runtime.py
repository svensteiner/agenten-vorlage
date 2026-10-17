"""Durable host phase ordering; independent of the model's chosen workflow."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from .contracts import ContractError
from .phase_test_execution import LocalPhaseTestPolicy, authorize_phase, verify_phase_freshness
from .phase_test_runner import run_phase, validate_phase_receipt


class LocalPhaseProposalRejected(ContractError):
    """A known proposal guard rejected an action before any side effect."""


class LocalPhaseRuntime:
    max_attempts = 32

    def __init__(self, policy: LocalPhaseTestPolicy, workspace: Path, run_id: str,
                 state: dict, checkpoint: Callable[[], None]):
        self.policy, self.workspace, self.run_id = policy, workspace, run_id
        self.checkpoint = checkpoint
        self.state = state
        if (type(state) is not dict or set(state) != {"policy_sha256", "attempts", "in_flight"}
                or state["policy_sha256"] != policy.sha256
                or type(state["attempts"]) is not list or len(state["attempts"]) > self.max_attempts):
            raise ContractError("Persisted local phase state is invalid or belongs to another policy.")
        for receipt in state["attempts"]:
            validate_phase_receipt(receipt, policy, run_id)
        if state["in_flight"] is not None or any(
                receipt["status"] == "unknown" for receipt in state["attempts"]):
            raise ContractError("Unknown local phase outcome blocks further execution; it cannot be replayed.")
        previous: dict[str, dict] = {}
        red_paths = {path for path in policy.snapshot_paths if path.startswith("tests/")}
        for receipt in state["attempts"]:
            phase = receipt["phase"]
            if phase == "red":
                if any(receipt["input_hashes"].get(path) != digest
                       for path, digest in policy.production_hashes):
                    raise ContractError("Persisted RED did not use the pinned production baseline.")
                previous.pop("targeted", None)
            else:
                red = previous.get("red")
                if (not red or red["status"] != "passed" or any(
                        red["input_hashes"].get(path) != receipt["input_hashes"].get(path)
                        for path in red_paths)):
                    raise ContractError("Persisted regression phase precedes its valid RED.")
                targeted = previous.get("targeted")
                if phase == "full" and not (
                        targeted and targeted["status"] == "passed"
                        and targeted["snapshot_sha256"] == receipt["snapshot_sha256"]):
                    raise ContractError("Persisted full phase precedes its fresh targeted result.")
            previous[phase] = receipt

    @staticmethod
    def initial_state(policy: LocalPhaseTestPolicy) -> dict:
        return {"policy_sha256": policy.sha256, "attempts": [], "in_flight": None}

    def _latest(self, phase: str) -> dict | None:
        return next((r for r in reversed(self.state["attempts"]) if r["phase"] == phase), None)

    def _red_is_current(self, hashes: dict) -> bool:
        receipt = self._latest("red")
        test_paths = {path for path in self.policy.snapshot_paths if path.startswith("tests/")}
        return bool(receipt and receipt["status"] == "passed" and all(
            receipt["input_hashes"].get(path) == hashes.get(path) for path in test_paths))

    def execute(self, phase: str, timeout: float) -> dict:
        authorize_phase(self.policy, phase)
        if self.state["in_flight"] is not None:
            raise ContractError("An uncertain phase cannot be followed by another attempt.")
        freshness = verify_phase_freshness(self.policy, self.workspace, phase)
        if any(receipt["phase"] == phase and receipt["snapshot_sha256"] == freshness["snapshot_sha256"]
               for receipt in self.state["attempts"]):
            raise LocalPhaseProposalRejected(
                "This phase already has a terminal result for the identical snapshot."
            )
        if phase != "red" and not self._red_is_current(freshness["input_hashes"]):
            raise LocalPhaseProposalRejected(
                "Regression phases require a reproduced RED with unchanged regression tests."
            )
        targeted = self._latest("targeted")
        if phase == "full" and not (
                targeted and targeted["status"] == "passed"
                and targeted["snapshot_sha256"] == freshness["snapshot_sha256"]):
            raise LocalPhaseProposalRejected(
                "Full verification requires a passing targeted phase for the current snapshot."
            )
        if len(self.state["attempts"]) >= self.max_attempts:
            raise ContractError("Local phase attempt budget exhausted.")
        self.state["in_flight"] = {"phase": phase, "snapshot_sha256": freshness["snapshot_sha256"]}
        self.checkpoint()
        # Keep the durable reservation on every exception. A returned receipt
        # alone permits clearing it only after complete host validation.
        try:
            raw_receipt = run_phase(
                self.policy, self.workspace, phase, run_id=self.run_id,
                timeout=timeout,
                results_dir=self.policy.source_path.parent / "phase-results",
            )
        except LocalPhaseProposalRejected as exc:
            # Once reserved, even a specially typed exception is no longer a
            # safe proposal correction: the external phase may have started.
            raise ContractError(
                "A phase proposal rejection occurred after reservation."
            ) from exc
        receipt = validate_phase_receipt(raw_receipt, self.policy, self.run_id)
        if receipt["phase"] != phase or receipt["snapshot_sha256"] != freshness["snapshot_sha256"]:
            raise ContractError("Phase receipt does not match the dispatched phase and snapshot.")
        self.state["attempts"].append(receipt)
        if receipt["status"] != "unknown":
            self.state["in_flight"] = None
        self.checkpoint()
        if receipt["status"] == "unknown":
            raise ContractError("Local phase outcome is unknown; further attempts are blocked.")
        return receipt

    def authorize_mutation(self, tool: str, arguments: dict) -> None:
        if tool not in {"write_file", "edit_file"} or type(arguments) is not dict:
            raise ContractError("Private phase execution permits only bounded host file mutations.")
        relative = self.policy.authorize_write(arguments.get("path"))
        if relative in dict(self.policy.production_hashes):
            current = verify_phase_freshness(self.policy, self.workspace, "targeted")
            if not self._red_is_current(current["input_hashes"]):
                raise LocalPhaseProposalRejected(
                    "Production changes require a reproduced RED with unchanged regression tests."
                )

    def require_completion(self) -> None:
        if self.state["in_flight"] is not None:
            raise ContractError("Local test phase remains unresolved.")
        freshness = verify_phase_freshness(self.policy, self.workspace, "full")
        attempts = self.state["attempts"]
        if not attempts or not self._red_is_current(freshness["input_hashes"]):
            raise ContractError("Completion requires an unchanged, reproduced regression test.")
        full = attempts[-1]
        targeted = self._latest("targeted")
        if (full["phase"] != "full" or full["status"] != "passed"
                or full["snapshot_sha256"] != freshness["snapshot_sha256"]
                or not targeted or targeted["status"] != "passed"
                or targeted["snapshot_sha256"] != freshness["snapshot_sha256"]):
            raise ContractError("Completion requires fresh passing targeted and full phases.")

    def summary(self) -> dict:
        return {"policy_sha256": self.policy.sha256,
                "phases": ["red", "targeted", "full"],
                "attempts_used": len(self.state["attempts"]), "max_attempts": self.max_attempts,
                "latest": {phase: {key: receipt[key] for key in ("status", "reason", "receipt_sha256")}
                           for phase in ("red", "targeted", "full")
                           if (receipt := self._latest(phase)) is not None}}
