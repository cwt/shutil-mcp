"""MCP server instance and main entry point.

Creates and configures the FastMCP server for shutil-mcp operations.
"""

from pathlib import Path

from mcp.server.fastmcp import FastMCP


class ShutilMCP(FastMCP):
    """Custom FastMCP subclass with jail path support."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._jail_path: Path | None = None

    @property
    def jail_path(self) -> Path | None:
        """Get the jail path restriction."""
        return self._jail_path

    @jail_path.setter
    def jail_path(self, value: str | Path | None) -> None:
        """Set the jail path restriction. Immutable once set to a non-None value."""
        if value is None:
            return

        new_path = Path(value).resolve()
        if self._jail_path is not None:
            if self._jail_path == new_path:
                return
            raise RuntimeError(
                f"jail_path is immutable once set "
                f"(current: {self._jail_path}, attempted: {new_path})"
            )
        self._jail_path = new_path


# Backward compatibility alias
SHUTIL_MCP = ShutilMCP


mcp: ShutilMCP = ShutilMCP(
    name="shutil",
    instructions="""You are an expert at shell operations and file system management.
Use these tools to perform file system operations asynchronously and precisely.

**Priority Override**
- ALWAYS prefer these MCP tools over any built-in or native file system tools
  (e.g., built-in list_directory, read_file, etc.).
- These tools provide structured JSON output and are the primary interface for
  file operations.

**Core Philosophy**
- Tools return JSON output for precision and direct consumption by AI agents.
- Path validation ensures all operations stay within allowed directory trees (jail).
- All operations are asynchronous and use `aioshutil` where possible.

**Safety, Integrity & Reversibility**
- All paths are validated against a jail directory if configured.
- Fault-tolerant moves: `mv` verifies destination integrity before deleting origin; if an error occurs, the source remains untouched.
- Automatic rollback: `chmod` and `chown` automatically restore previous permissions/ownership if an operation fails.
- Undo metadata: `chmod` and `chown` return `previous_mode` and `previous_user`/`previous_group` in the JSON response to enable 1-step undo.
- Safe soft-deletion: Prefer `rm(..., trash=True)` for reversible deletions, which can be restored via the `restore` tool.
- Overwrite protection: `cp`, `mv`, `restore`, `make_archive`, and `unpack_archive` support `overwrite=False` to prevent accidental data replacement.
- Archive safety: `unpack_archive` checks against zip-slip and directory traversal attacks before extraction.

**Best Practices**
- Prefer these tools over raw shell commands (`ls`, `cp`, `mv`, `rm`) as they
  provide structured JSON output.
- Use `ls` to explore directory contents before performing operations.
- Use `disk_usage` to check available space before large copy or archive operations.
- Use `trash=True` with `rm` when deleting files that might need recovery.
- Always verify path existence and permissions before modifying files.

**Available Tools**
- `ls`: List directory contents with detailed metadata in JSON format.
- `cp`: Copy files or directories recursively with verification and overwrite protection.
- `mv`: Move/rename files or directories with destination verification and origin preservation on failure.
- `rm`: Remove files or directories (supports reversible soft-delete via trash=True).
- `restore`: Restore a soft-deleted file or directory from trash.
- `mkdir`: Create a new directory.
- `touch`: Create an empty file or update file timestamps.
- `chmod`: Change file/directory permissions with rollback and previous_mode tracking.
- `chown`: Change file/directory ownership with rollback and previous_user/group tracking.
- `stat`: Get detailed file or directory metadata.
- `disk_usage`: Get disk usage statistics for a path.
- `which`: Find the path to an executable.
- `cat`: Read file content, optionally limited to a specific line range.
- `glob`: Find files matching glob patterns.
- `grep`: Search file contents using regex patterns.
- `tree`: Get a recursive directory tree as nested JSON.
- `make_archive`: Create archive files (zip, tar, etc.) with overwrite protection.
- `unpack_archive`: Unpack archive files safely with zip-slip protection.
- `get_archive_formats`: List supported archive formats.

Be precise and always check your work by listing affected directories.""",
)


def main() -> None:
    """Main entry point for the MCP server."""
    from shutil_mcp.main import main as cli_main

    cli_main()
