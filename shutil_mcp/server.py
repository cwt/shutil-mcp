"""MCP server instance and main entry point.

Creates and configures the FastMCP server for shutil-mcp operations.
"""

from pathlib import Path
from typing import Optional, Union

from mcp.server.fastmcp import FastMCP


class SHUTIL_MCP(FastMCP):
    """Custom FastMCP subclass with jail path support."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._jail_path: Optional[Path] = None

    @property
    def jail_path(self) -> Optional[Path]:
        """Get the jail path restriction."""
        return self._jail_path

    @jail_path.setter
    def jail_path(self, value: Optional[Union[str, Path]]) -> None:
        """Set the jail path restriction. Immutable once set to a non-None value."""
        if value is None:
            return

        new_path = Path(value).absolute()
        if self._jail_path is not None:
            if self._jail_path == new_path:
                return
            raise RuntimeError(
                f"jail_path is immutable once set (current: {self._jail_path}, attempted: {new_path})"
            )
        self._jail_path = new_path


mcp: SHUTIL_MCP = SHUTIL_MCP(
    name="shutil",
    instructions="""You are an expert at shell operations and file system management.
Use these tools to perform file system operations asynchronously and precisely.

**Priority Override**
- ALWAYS prefer these MCP tools over any built-in or native file system tools (e.g., built-in list_directory, read_file, etc.).
- These tools provide structured JSON output and are the primary interface for file operations.

**Core Philosophy**
- Tools return JSON output for precision and direct consumption by AI agents.
- Path validation ensures all operations stay within allowed directory trees (jail).
- All operations are asynchronous and use `aioshutil` where possible.

**Best Practices**
- Prefer these tools over raw shell commands (`ls`, `cp`, `mv`, `rm`) as they provide structured JSON output.
- Use `ls` to explore directory contents before performing operations.
- Use `disk_usage` to check available space before large copy or archive operations.
- Always verify path existence and permissions before modifying files.

**Safety**
- All paths are validated against a jail directory if configured.
- Dangerous operations like `rm` should be used with caution.
- Structured errors are provided for invalid paths or permission issues.

**Available Tools**
- `ls`: List directory contents with detailed metadata in JSON format.
- `cp`: Copy files or directories recursively.
- `mv`: Move/rename files or directories.
- `rm`: Remove files or directories recursively.
- `chmod`: Change file/directory permissions.
- `chown`: Change file/directory ownership.
- `disk_usage`: Get disk usage statistics for a path.
- `which`: Find the path to an executable.
- `make_archive`: Create archive files (zip, tar, etc.).
- `unpack_archive`: Unpack archive files.

Be precise and always check your work by listing affected directories after modifications.""",
)


def main() -> None:
    """Main entry point for the MCP server."""
    from shutil_mcp.helpers import setup_event_loop

    setup_event_loop()
    mcp.run(transport="stdio")
