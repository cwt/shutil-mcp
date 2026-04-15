"""Tool registrations for shutil-mcp.

Exports all file system tools to be registered with the MCP server.
"""

from shutil_mcp.tools.archive import (
    get_archive_formats,
    make_archive,
    unpack_archive,
)
from shutil_mcp.tools.file_ops import (
    chmod,
    chown,
    cp,
    mv,
    rm,
    which,
)
from shutil_mcp.tools.listing import (
    disk_usage,
    ls,
)

__all__ = [
    "ls",
    "disk_usage",
    "cp",
    "mv",
    "rm",
    "chmod",
    "chown",
    "which",
    "make_archive",
    "unpack_archive",
    "get_archive_formats",
]
