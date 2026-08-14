"""Tool registrations for shutil-mcp.

Exports all file system tools to be registered with the MCP server.
"""

from shutil_mcp.tools.archive import (
    get_archive_formats,
    make_archive,
    unpack_archive,
)
from shutil_mcp.tools.file_ops import (
    cat,
    chmod,
    chown,
    cp,
    mkdir,
    mv,
    restore,
    rm,
    touch,
    which,
)
from shutil_mcp.tools.listing import (
    disk_usage,
    ls,
    stat,
)
from shutil_mcp.tools.search import (
    glob,
    grep,
    tree,
)

__all__ = [
    "ls",
    "stat",
    "disk_usage",
    "cp",
    "mv",
    "rm",
    "restore",
    "mkdir",
    "touch",
    "chmod",
    "chown",
    "which",
    "cat",
    "glob",
    "grep",
    "tree",
    "make_archive",
    "unpack_archive",
    "get_archive_formats",
]
