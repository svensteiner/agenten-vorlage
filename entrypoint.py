"""Unified entrypoint for the future agent template.

For now this keeps compatibility with the existing agent implementation.
The long-term goal is to route this through core.orchestrator.AgentOrchestrator.
"""

from agent import main


if __name__ == "__main__":
    main()
