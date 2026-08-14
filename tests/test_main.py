import pytest

from shutil_mcp import tools
from shutil_mcp.server import mcp


@pytest.mark.asyncio
async def test_all_tools_registered() -> None:
    # Ensure every tool listed in tools.__all__ is registered with FastMCP
    tool_names = set(tools.__all__)
    registered_tools = await mcp.list_tools()
    registered_names = {t.name for t in registered_tools}

    for name in tool_names:
        assert (
            name in registered_names
        ), f"Tool '{name}' is not registered on mcp"
