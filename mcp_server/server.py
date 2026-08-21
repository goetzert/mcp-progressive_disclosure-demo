from fastmcp import FastMCP

mcp = FastMCP("Progressive Disclosure Demo")

from mcp_server.tools import weather, customers, orders, finance, dummy  # noqa: E402, F401

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8000,
    )
