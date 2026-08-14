"""Archive management tools.

Provides 'make_archive' and 'unpack_archive' tools.
"""

import json
from pathlib import Path

import aioshutil
from mcp.types import TextContent

from shutil_mcp.decorators import handle_errors, json_tool
from shutil_mcp.helpers import (
    validate_dir_path,
    validate_path,
    validate_path_in_jail,
)
from shutil_mcp.server import mcp


@mcp.tool()
@handle_errors
@json_tool
async def make_archive(
    base_name: str,
    format: str,
    root_dir: str | None = None,
    base_dir: str | None = None,
) -> list[TextContent]:
    """Create an archive file (zip, tar, etc.).

    Args:
        base_name: Name of the file to create (including path)
        format: Archive format (e.g., 'zip', 'tar', 'gztar')
        root_dir: Directory that will be the root of the archive (default: current)
        base_dir: Directory from which archiving starts (default: current)
    """
    # base_name must be in jail
    base_path = Path(base_name).absolute()
    base_path = validate_path_in_jail(base_path)

    r_dir = validate_dir_path(root_dir) if root_dir else None

    if base_dir:
        if r_dir:
            check_b_dir = (r_dir / base_dir).resolve()
            validate_path_in_jail(check_b_dir)
            b_dir_str = base_dir
        else:
            b_dir = validate_path(base_dir)
            b_dir_str = str(b_dir)
    else:
        b_dir_str = None

    archive_path = await aioshutil.make_archive(
        str(base_path),
        format,
        root_dir=str(r_dir) if r_dir else None,
        base_dir=b_dir_str,
    )

    return json.dumps(
        {
            "operation": "make_archive",
            "archive_file": archive_path,
            "format": format,
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def unpack_archive(
    filename: str,
    extract_dir: str | None = None,
    format: str | None = None,
) -> list[TextContent]:
    """Unpack an archive file.

    Args:
        filename: Path to the archive
        extract_dir: Directory to extract into (default: current)
        format: Archive format (optional)
    """
    archive_file = validate_path(filename)
    if extract_dir:
        e_dir = validate_dir_path(extract_dir, create_if_missing=True)
    elif mcp.jail_path:
        e_dir = mcp.jail_path.resolve()
    else:
        e_dir = Path(".").resolve()

    e_dir = validate_path_in_jail(e_dir)

    await aioshutil.unpack_archive(
        str(archive_file), extract_dir=str(e_dir), format=format
    )

    return json.dumps(
        {
            "operation": "unpack_archive",
            "archive_file": str(archive_file),
            "extract_dir": str(e_dir),
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def get_archive_formats() -> list[TextContent]:
    """Get a list of supported archive formats."""
    import shutil

    formats = shutil.get_archive_formats()
    return json.dumps(
        [{"name": f[0], "description": f[1]} for f in formats],
        separators=(",", ":"),
    )  # type: ignore[return-value]
