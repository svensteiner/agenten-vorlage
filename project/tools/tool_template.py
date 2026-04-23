"""Template for a project-specific tool.

Copy this file when adding a new automation capability and replace the
implementation with the project-specific adapter.
"""

from tools.base_tool import BaseTool


class ProjectTool(BaseTool):
    name = "project_tool"
    description = "Template project tool. Replace with a real implementation."

    def run(self, input: str) -> str:
        return f"Template tool received: {input}"
