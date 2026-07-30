"""Fail-closed capabilities for a generated KMU controlling instance."""

from .tools import ControllingComputeTool, InstanceReadTool
from .narrative import ControllingReportTool
from .artifacts import read_verified_latest_report_html

__all__ = [
    "ControllingComputeTool",
    "ControllingReportTool",
    "InstanceReadTool",
    "read_verified_latest_report_html",
]
