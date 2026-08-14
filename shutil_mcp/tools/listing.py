"""Directory listing and disk usage tools.

Provides 'ls' and 'disk_usage' tools with JSON output for AI agents.
"""

import json
import os
import stat as stat_module
from datetime import datetime
from typing import Any

from mcp.types import TextContent

from shutil_mcp.decorators import handle_errors, json_tool
from shutil_mcp.helpers import validate_dir_path, validate_path
from shutil_mcp.server import mcp


@mcp.tool()
@handle_errors
@json_tool
async def ls(path: str = ".") -> list[TextContent]:
    """List directory contents with detailed metadata.

    Args:
        path: Directory path to list (default: ".")
    """
    dir_path = validate_dir_path(path)

    import asyncio

    loop = asyncio.get_running_loop()

    def _entry_sort_key(item: dict[str, Any]) -> tuple[bool, str]:
        return (item["type"] != "directory", item["name"])

    def get_entries() -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        with os.scandir(dir_path) as scandir_it:
            for entry in scandir_it:
                try:
                    is_symlink = entry.is_symlink()
                except OSError:
                    is_symlink = False

                if is_symlink:
                    entry_type = "symlink"
                elif entry.is_dir(follow_symlinks=False):
                    entry_type = "directory"
                elif entry.is_file(follow_symlinks=False):
                    entry_type = "file"
                else:
                    entry_type = "other"

                try:
                    s = entry.stat(follow_symlinks=False)
                    mode = s.st_mode
                    size = s.st_size
                    mtime = datetime.fromtimestamp(s.st_mtime).isoformat()
                    oct_mode = oct(stat_module.S_IMODE(mode))
                    owner = s.st_uid
                    group = s.st_gid
                except OSError:
                    size = 0
                    mtime = ""
                    oct_mode = "0o0"
                    owner = 0
                    group = 0

                entries.append(
                    {
                        "name": entry.name,
                        "type": entry_type,
                        "size": size,
                        "mtime": mtime,
                        "mode": oct_mode,
                        "owner": owner,
                        "group": group,
                    }
                )
        return entries

    entries = await loop.run_in_executor(None, get_entries)
    entries.sort(key=_entry_sort_key)

    return json.dumps(entries, separators=(",", ":"))  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def disk_usage(path: str = ".") -> list[TextContent]:
    """Get disk usage statistics for a path.

    Args:
        path: Path to check disk usage for (default: ".")
    """
    check_path = validate_path(path)

    import aioshutil

    usage = await aioshutil.disk_usage(check_path)

    return json.dumps(
        {
            "path": str(check_path),
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent_used": (
                round((usage.used / usage.total) * 100, 2)
                if usage.total > 0
                else 0
            ),
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def stat(
    path: str,
) -> list[TextContent]:
    """Get detailed file or directory metadata.

    Args:
        path: Path to the file or directory
    """
    target = validate_path(path)
    import asyncio

    loop = asyncio.get_running_loop()

    def _stat() -> dict[str, object]:
        s = os.stat(target, follow_symlinks=True)
        mode = s.st_mode

        if stat_module.S_ISDIR(mode):
            entry_type = "directory"
        elif stat_module.S_ISLNK(mode):
            entry_type = "symlink"
        elif stat_module.S_ISREG(mode):
            entry_type = "file"
        elif stat_module.S_ISFIFO(mode):
            entry_type = "fifo"
        elif stat_module.S_ISSOCK(mode):
            entry_type = "socket"
        elif stat_module.S_ISBLK(mode):
            entry_type = "block_device"
        elif stat_module.S_ISCHR(mode):
            entry_type = "char_device"
        else:
            entry_type = "other"

        return {
            "path": str(target),
            "type": entry_type,
            "size": s.st_size,
            "mode": oct(stat_module.S_IMODE(mode)),
            "owner": s.st_uid,
            "group": s.st_gid,
            "atime": datetime.fromtimestamp(s.st_atime).isoformat(),
            "mtime": datetime.fromtimestamp(s.st_mtime).isoformat(),
            "ctime": datetime.fromtimestamp(s.st_ctime).isoformat(),
            "device": s.st_dev,
            "inode": s.st_ino,
            "nlink": s.st_nlink,
        }

    result = await loop.run_in_executor(None, _stat)

    return json.dumps(result, separators=(",", ":"))  # type: ignore[return-value]
