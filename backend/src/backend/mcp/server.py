"""FastMCP server exposing the health assessment tools.

Run it standalone (stdio transport) with::

    python -m backend.mcp.server

The tools themselves live in :mod:`backend.mcp.tools`; this module only wires
them onto an MCP server so agents (Memory, Risk, Monitoring, Response - built in
later modules) can call them over the Model Context Protocol.

The ``fastmcp`` / ``mcp`` packages are optional at import time so the HTTP API and
the test suite keep working without them; calling :func:`create_mcp_server`
without the dependency raises a clear error.
"""

import inspect


def _load_fastmcp():
    """Import ``FastMCP`` from whichever optional MCP package is installed.

    Returns:
        The ``FastMCP`` class, or ``None`` when no MCP package is available.
    """
    try:  # standalone package declared in the project stack
        from fastmcp import FastMCP  # type: ignore[import-not-found]
    except ImportError:
        pass
    else:
        return FastMCP

    try:  # official MCP SDK ships the same server implementation
        from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]
    except ImportError:
        return None
    return FastMCP


# ``None`` means "MCP support not installed" - see :func:`create_mcp_server`.
FastMCP = _load_fastmcp()

from backend.mcp.tools import TOOL_FUNCTIONS

SERVER_NAME = "healthcare-assistant-health-assessment"

INSTRUCTIONS = """
Read access to the patient onboarding survey (Module 1).

Use `get_health_assessment_status` first to check whether a patient completed the
survey, `get_health_assessment_summary` for compact risk signals and
`get_patient_health_assessment` for the full set of answers. All tools are
read-only and take the existing patient_id; no patient records are created.
""".strip()


def create_mcp_server() -> "FastMCP":
    """Create the FastMCP server with the health assessment tools registered.

    Returns:
        A ready-to-run ``FastMCP`` server instance.

    Raises:
        RuntimeError: when the optional ``mcp`` dependency is not installed.
    """
    if FastMCP is None:  # pragma: no cover
        raise RuntimeError(
            "The 'fastmcp' package is required to run the MCP server. "
            "Install it with: uv add fastmcp"
        )
    server = FastMCP(name=SERVER_NAME, instructions=INSTRUCTIONS)
    for tool in TOOL_FUNCTIONS:
        # ``FastMCP.tool()`` uses the function name and its docstring as the tool
        # description, which is why every tool carries a full docstring.
        server.tool()(tool)
        assert inspect.getdoc(tool), f"tool {tool.__name__} needs a docstring"
    return server


def main() -> None:
    """Run the MCP server over stdio (default agent transport)."""
    server = create_mcp_server()
    server.run()


if __name__ == "__main__":  # pragma: no cover
    main()