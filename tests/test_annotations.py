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
        assert isinstance(
            annotations.readOnlyHint, bool
        ), f"Tool '{tool.name}' readOnlyHint is not bool: {annotations.readOnlyHint}"
        assert isinstance(
            annotations.destructiveHint, bool
        ), f"Tool '{tool.name}' destructiveHint not bool: {annotations.destructiveHint}"
        assert isinstance(
            annotations.idempotentHint, bool
        ), f"Tool '{tool.name}' idempotentHint not bool: {annotations.idempotentHint}"
        assert isinstance(
            annotations.openWorldHint, bool
        ), f"Tool '{tool.name}' openWorldHint not bool: {annotations.openWorldHint}"


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
            tool.annotations.destructiveHint is True
        ), f"Tool '{name}' should have destructiveHint=True"
        assert (
            tool.annotations.readOnlyHint is False
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
            tool.annotations.readOnlyHint is True
        ), f"Tool '{name}' should have readOnlyHint=True"
        assert (
            tool.annotations.destructiveHint is False
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
            tool.annotations.readOnlyHint is False
        ), f"Tool '{name}' should have readOnlyHint=False"
        assert (
            tool.annotations.destructiveHint is False
        ), f"Tool '{name}' should have destructiveHint=False"


@pytest.mark.asyncio
async def test_all_tools_declare_input_schema() -> None:
    """Verify 100% of tools declare an object inputSchema."""
    tools = await mcp.list_tools()
    assert len(tools) > 0

    for tool in tools:
        assert (
            tool.inputSchema is not None
        ), f"Tool '{tool.name}' is missing inputSchema"
        assert isinstance(
            tool.inputSchema, dict
        ), f"Tool '{tool.name}' inputSchema is not a dict"
        assert (
            tool.inputSchema.get("type") == "object"
        ), f"Tool '{tool.name}' inputSchema type is not 'object'"
        assert (
            "properties" in tool.inputSchema
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
