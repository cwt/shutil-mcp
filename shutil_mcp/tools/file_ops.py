"""File operations tools.

Provides 'cp', 'mv', 'rm', 'chown', 'chmod', and 'which' tools.
"""

import json
import os
from pathlib import Path

import aioshutil
from mcp.types import TextContent

from shutil_mcp.decorators import handle_errors, json_tool
from shutil_mcp.helpers import validate_path, validate_path_in_jail
from shutil_mcp.server import mcp


@mcp.tool()
@handle_errors
@json_tool
async def cp(
    src: str, dst: str, follow_symlinks: bool = True
) -> list[TextContent]:
    """Copy files or directories recursively.

    Args:
        src: Source path
        dst: Destination path
        follow_symlinks: Whether to follow symlinks (default: True)
    """
    source = validate_path(src)
    # Destination must be in jail, but it might not exist yet
    dest = Path(dst).absolute()
    dest = validate_path_in_jail(dest)

    if source.is_dir():
        await aioshutil.copytree(
            source, dest, symlinks=not follow_symlinks, dirs_exist_ok=True
        )
        op_type = "directory_copy"
    else:
        await aioshutil.copy2(source, dest, follow_symlinks=follow_symlinks)
        op_type = "file_copy"

    return json.dumps(
        {
            "operation": op_type,
            "src": str(source),
            "dst": str(dest),
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def mv(src: str, dst: str) -> list[TextContent]:
    """Move or rename files or directories.

    Args:
        src: Source path
        dst: Destination path
    """
    source = validate_path(src)
    dest = Path(dst).absolute()
    dest = validate_path_in_jail(dest)

    await aioshutil.move(source, dest)

    return json.dumps(
        {
            "operation": "move",
            "src": str(source),
            "dst": str(dest),
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def rm(path: str, recursive: bool = False) -> list[TextContent]:
    """Remove files or directories.

    Args:
        path: Path to remove
        recursive: Whether to remove recursively if it's a directory (default: False)
    """
    target = validate_path(path)

    if target.is_dir():
        if not recursive:
            raise ValueError(
                f"'{target}' is a directory. Use recursive=True to remove."
            )
        await aioshutil.rmtree(target)
        op_type = "directory_removal"
    else:
        # Run in thread since os.remove is blocking
        import asyncio

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, os.remove, target)
        op_type = "file_removal"

    return json.dumps(
        {"operation": op_type, "path": str(target), "status": "success"},
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def chmod(path: str, mode: int) -> list[TextContent]:
    """Change file or directory permissions.

    Args:
        path: Path to modify
        mode: Numeric mode (octal, e.g., 0o755)
    """
    target = validate_path(path)

    # Run in thread since os.chmod is blocking
    import asyncio

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, os.chmod, target, mode)

    return json.dumps(
        {
            "operation": "chmod",
            "path": str(target),
            "mode": oct(mode),
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def chown(
    path: str, user: str | None = None, group: str | None = None
) -> list[TextContent]:
    """Change file or directory ownership.

    Args:
        path: Path to modify
        user: Username or UID (default: None)
        group: Group name or GID (default: None)
    """
    target = validate_path(path)

    # Use type ignore if mypy stubs for aioshutil are incorrect
    await aioshutil.chown(str(target), user=user, group=group)  # type: ignore[arg-type]

    return json.dumps(
        {
            "operation": "chown",
            "path": str(target),
            "user": user,
            "group": group,
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def which(cmd: str, path: str | None = None) -> list[TextContent]:
    """Find the path to an executable.

    Args:
        cmd: Executable name
        path: Search path (default: None, uses system PATH)
    """
    found_path = await aioshutil.which(cmd, path=path)

    return json.dumps(
        {
            "command": cmd,
            "path": found_path,
            "status": "found" if found_path else "not_found",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]
