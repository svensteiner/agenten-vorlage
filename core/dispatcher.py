"""Execution layer for tools and subagents."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DispatchResult:
    success: bool
    output: str = ""
    tool: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Dispatcher:
    """Routes plan steps to tools or subagents.

    In the target architecture this becomes the only place that is allowed to
    perform side effects.
    """

    def dispatch(self, step, tools: dict[str, Any] | None = None) -> DispatchResult:
        tools = tools or {}
        if step.tool and step.tool in tools:
            output = tools[step.tool].safe_run(step.input or "")
            return DispatchResult(success=not output.startswith("FEHLER"), output=output, tool=step.tool)
        if step.tool and step.tool not in tools:
            return DispatchResult(
                success=False,
                output=f"FEHLER: Tool '{step.tool}' is not available.",
                tool=step.tool,
                metadata={"step": step.id},
            )
        if step.action in {"use_tool", "notify"} and not step.tool:
            return DispatchResult(
                success=False,
                output=f"FEHLER: Step '{step.id}' requires a tool but none was selected.",
                metadata={"step": step.id, "action": step.action},
            )
        return DispatchResult(
            success=True,
            output=f"Planned step recorded: {step.description}",
            tool=step.tool,
            metadata={"step": step.id, "action": step.action},
        )
