"""Reusable agent core package.

This package is intentionally thin at first: it defines the target
architecture so project-specific automations can be layered on top.
"""

from .context import ContextBuilder, ProjectContext
from .dispatcher import DispatchResult, Dispatcher
from .governance import GovernanceDecision, GovernancePolicy
from .memory import MemoryStore
from .orchestrator import AgentOrchestrator, RunResult
from .planner import Plan, PlanStep, Planner
from .runtime import RuntimeState, RuntimeStore
from .verifier import VerificationResult, Verifier

__all__ = [
    "AgentOrchestrator",
    "ContextBuilder",
    "DispatchResult",
    "Dispatcher",
    "GovernanceDecision",
    "GovernancePolicy",
    "MemoryStore",
    "Plan",
    "PlanStep",
    "Planner",
    "ProjectContext",
    "RunResult",
    "RuntimeState",
    "RuntimeStore",
    "VerificationResult",
    "Verifier",
]
