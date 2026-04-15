"""Directory listing and disk usage tools.

Provides 'ls' and 'disk_usage' tools with JSON output for AI agents.
"""

import json
import os
import stat
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

    def get_entries() -> list[dict[str, Any]]:
        entries = []
        for entry in os.scandir(dir_path):
            s = entry.stat()
            mode = s.st_mode

            # Determine entry type
            if stat.S_ISDIR(mode):
                entry_type = "directory"
            elif stat.S_ISLNK(mode):
                entry_type = "symlink"
            elif stat.S_ISREG(mode):
                entry_type = "file"
            else:
                entry_type = "other"

            entries.append(
                {
                    "name": entry.name,
                    "type": entry_type,
                    "size": s.st_size,
                    "mtime": datetime.fromtimestamp(s.st_mtime).isoformat(),
                    "mode": oct(stat.S_IMODE(mode)),
                    "owner": s.st_uid,
                    "group": s.st_gid,
                }
            )
        return entries

    entries = await loop.run_in_executor(None, get_entries)

    # Sort entries: directories first, then files, both alphabetically
    entries.sort(key=lambda x: (x["type"] != "directory", x["name"]))

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
