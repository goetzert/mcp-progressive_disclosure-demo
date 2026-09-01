"""In-memory MCP client that talks to the FastMCP server instance directly.

Because the MCP server and backend run in the same process, we use FastMCP's
in-memory transport (``Client(mcp)``) instead of HTTP/SSE. This avoids
Windows-specific SSE issues and keeps the setup simple.
"""

from fastmcp import Client
from mcp_server.server import mcp


def _tool_to_dict(tool) -> dict:
    """Convert a FastMCP tool object into a plain dict for JSON serialisation."""
    return {
        "name": tool.name,
        "description": tool.description or "",
        "parameters": tool.inputSchema if hasattr(tool, "inputSchema") else {},
    }


async def list_all_tools() -> list[dict]:
    """Retrieve all registered tools from the MCP server.

    Returns:
        A list of tool dicts, each containing ``name``, ``description``, and
        ``parameters`` keys.
    """
    client = Client(mcp)
    async with client:
        tools = await client.list_tools()
        return [_tool_to_dict(t) for t in tools]


async def call_tool(name: str, arguments: dict) -> dict:
    """Call a tool on the MCP server and return its structured result.

    Args:
        name: The tool name (as registered with FastMCP).
        arguments: A dict of argument name → value.

    Returns:
        The tool's structured content if available, otherwise a dict with a
        ``text`` key extracted from the raw content blocks.
    """
    client = Client(mcp)
    async with client:
        result = await client.call_tool(name, arguments)
        if hasattr(result, "structured_content") and result.structured_content:
            return result.structured_content
        if hasattr(result, "content") and result.content:
            for block in result.content:
                if hasattr(block, "text"):
                    return {"text": block.text}
        return {}
