"""Tests for tool annotations, hints, input schemas, and error handling."""

import pytest
from mcp.types import ToolAnnotations

import shutil_mcp.main  # noqa: F401
from shutil_mcp.server import mcp

EXPECTED_DESTRUCTIVE_TOOLS = {
    "cp",
    "mv",
    "rm",
    "restore",
    "empty_trash",
    "gc_trash",
    "make_archive",
    "unpack_archive",
}

EXPECTED_READ_ONLY_TOOLS = {
    "cat",
    "disk_usage",
    "get_archive_formats",
    "glob",
    "grep",
    "ls",
    "stat",
    "tree",
    "which",
}

EXPECTED_MUTATING_NON_DESTRUCTIVE_TOOLS = {
    "chmod",
    "chown",
    "mkdir",
    "touch",
}


def _get_hint(annotations: ToolAnnotations, name: str) -> bool | None:
    snake_map = {
        "readOnlyHint": "read_only_hint",
        "destructiveHint": "destructive_hint",
        "idempotentHint": "idempotent_hint",
        "openWorldHint": "open_world_hint",
    }
    snake = snake_map.get(name, name)
    if hasattr(annotations, snake):
        val = getattr(annotations, snake)
        if isinstance(val, bool):
            return val
    val = getattr(annotations, name, None)
    if isinstance(val, bool):
        return val
    return None


def _get_input_schema(tool: object) -> dict[str, object] | None:
    if hasattr(tool, "input_schema"):
        schema = getattr(tool, "input_schema")
        if isinstance(schema, dict):
            return schema
    if hasattr(tool, "inputSchema"):
        schema = getattr(tool, "inputSchema")
        if isinstance(schema, dict):
            return schema
    return None


@pytest.mark.asyncio
async def test_all_tools_have_all_four_hints_declared() -> None:
    """Verify every registered tool declares all 4 hints as explicit booleans."""
    tools = await mcp.list_tools()
    assert len(tools) >= 21

    for tool in tools:
        assert (
            tool.annotations is not None
        ), f"Tool '{tool.name}' is missing annotations"
        assert isinstance(
            tool.annotations, ToolAnnotations
        ), f"Tool '{tool.name}' annotations not ToolAnnotations instance"

        annotations = tool.annotations
        read_only = _get_hint(annotations, "readOnlyHint")
        destructive = _get_hint(annotations, "destructiveHint")
        idempotent = _get_hint(annotations, "idempotentHint")
        open_world = _get_hint(annotations, "openWorldHint")

        assert isinstance(
            read_only, bool
        ), f"Tool '{tool.name}' readOnlyHint is not bool: {read_only}"
        assert isinstance(
            destructive, bool
        ), f"Tool '{tool.name}' destructiveHint not bool: {destructive}"
        assert isinstance(
            idempotent, bool
        ), f"Tool '{tool.name}' idempotentHint not bool: {idempotent}"
        assert isinstance(
            open_world, bool
        ), f"Tool '{tool.name}' openWorldHint not bool: {open_world}"


@pytest.mark.asyncio
async def test_destructive_tools_classification() -> None:
    """Verify destructive tools have destructiveHint=True and readOnlyHint=False."""
    tools = await mcp.list_tools()
    tool_map = {tool.name: tool for tool in tools}

    for name in EXPECTED_DESTRUCTIVE_TOOLS:
        assert name in tool_map, f"Expected destructive tool '{name}' not found"
        tool = tool_map[name]
        assert tool.annotations is not None
        assert (
            _get_hint(tool.annotations, "destructiveHint") is True
        ), f"Tool '{name}' should have destructiveHint=True"
        assert (
            _get_hint(tool.annotations, "readOnlyHint") is False
        ), f"Tool '{name}' should have readOnlyHint=False"


@pytest.mark.asyncio
async def test_read_only_tools_classification() -> None:
    """Verify read-only tools have readOnlyHint=True and destructiveHint=False."""
    tools = await mcp.list_tools()
    tool_map = {tool.name: tool for tool in tools}

    for name in EXPECTED_READ_ONLY_TOOLS:
        assert name in tool_map, f"Expected read-only tool '{name}' not found"
        tool = tool_map[name]
        assert tool.annotations is not None
        assert (
            _get_hint(tool.annotations, "readOnlyHint") is True
        ), f"Tool '{name}' should have readOnlyHint=True"
        assert (
            _get_hint(tool.annotations, "destructiveHint") is False
        ), f"Tool '{name}' should have destructiveHint=False"


@pytest.mark.asyncio
async def test_mutating_non_destructive_tools_classification() -> None:
    """Verify mutating tools have readOnlyHint=False and destructiveHint=False."""
    tools = await mcp.list_tools()
    tool_map = {tool.name: tool for tool in tools}

    for name in EXPECTED_MUTATING_NON_DESTRUCTIVE_TOOLS:
        assert name in tool_map, f"Expected mutating tool '{name}' not found"
        tool = tool_map[name]
        assert tool.annotations is not None
        assert (
            _get_hint(tool.annotations, "readOnlyHint") is False
        ), f"Tool '{name}' should have readOnlyHint=False"
        assert (
            _get_hint(tool.annotations, "destructiveHint") is False
        ), f"Tool '{name}' should have destructiveHint=False"


@pytest.mark.asyncio
async def test_all_tools_declare_input_schema() -> None:
    """Verify 100% of tools declare an object inputSchema."""
    tools = await mcp.list_tools()
    assert len(tools) > 0

    for tool in tools:
        input_schema = _get_input_schema(tool)
        assert input_schema is not None, f"Tool '{tool.name}' is missing inputSchema"
        assert isinstance(
            input_schema, dict
        ), f"Tool '{tool.name}' inputSchema is not a dict"
        assert (
            input_schema.get("type") == "object"
        ), f"Tool '{tool.name}' inputSchema type is not 'object'"
        assert (
            "properties" in input_schema
        ), f"Tool '{tool.name}' inputSchema missing 'properties'"


@pytest.mark.asyncio
async def test_tool_handlers_catch_errors_gracefully() -> None:
    """Verify tool handlers catch exceptions and return structured error responses."""
    from shutil_mcp.tools.archive import make_archive, unpack_archive
    from shutil_mcp.tools.file_ops import (
        cat,
        chmod,
        chown,
        cp,
        mv,
        restore,
        rm,
    )
    from shutil_mcp.tools.listing import ls, stat
    from shutil_mcp.tools.search import glob, grep, tree

    # Invalid calls should return error responses without crashing
    res = await cat("/path/to/nonexistent/file/for/testing")
    assert res[0].text.startswith("Error:")

    res = await ls("/path/to/nonexistent/dir/for/testing")
    assert res[0].text.startswith("Error:")

    res = await stat("/path/to/nonexistent/file/for/testing")
    assert res[0].text.startswith("Error:")

    res = await cp("/path/to/nonexistent/src", "/tmp/dst")
    assert res[0].text.startswith("Error:")

    res = await mv("/path/to/nonexistent/src", "/tmp/dst")
    assert res[0].text.startswith("Error:")

    res = await rm("/path/to/nonexistent/file")
    assert res[0].text.startswith("Error:")

    res = await restore("/not/a/trash/path")
    assert res[0].text.startswith("Error:")

    res = await chmod("/path/to/nonexistent/file", 0o777)
    assert res[0].text.startswith("Error:")

    res = await chown("/path/to/nonexistent/file", "nonexistent_user")
    assert res[0].text.startswith("Error:")

    res = await glob("*.py", path="/path/to/nonexistent/dir")
    assert res[0].text.startswith("Error:")

    res = await grep("[invalid regex", path=".")
    assert res[0].text.startswith("Error:")

    res = await tree(path="/path/to/nonexistent/dir")
    assert res[0].text.startswith("Error:")

    res = await make_archive("/invalid/archive/target", "invalid_format")
    assert res[0].text.startswith("Error:")

    res = await unpack_archive("/invalid/nonexistent/archive.zip")
    assert res[0].text.startswith("Error:")
