"""MCP integration for the Healthcare Assistant.

The tool *logic* lives in :mod:`backend.mcp.tools` (framework-free and unit
tested); :mod:`backend.mcp.server` registers those tools on a FastMCP server so
the future Memory, Risk, Monitoring and Response agents can consume the survey
data over MCP instead of importing backend internals.
"""

from backend.mcp.tools import TOOL_FUNCTIONS

__all__ = ["TOOL_FUNCTIONS"]