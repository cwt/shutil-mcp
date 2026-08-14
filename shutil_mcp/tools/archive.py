"""Archive management tools.

Provides 'make_archive', 'unpack_archive', and 'get_archive_formats' tools.
"""

import asyncio
import json
from pathlib import Path

import aioshutil
from mcp.types import TextContent

from shutil_mcp.decorators import handle_errors, json_tool
from shutil_mcp.helpers import (
    validate_archive_safety,
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
    overwrite: bool = True,
) -> list[TextContent]:
    """Create an archive file (zip, tar, etc.) with overwrite protection.

    Args:
        base_name: Name of the file to create (including path)
        format: Archive format (e.g., 'zip', 'tar', 'gztar')
        root_dir: Directory that will be the root of the archive (default: current)
        base_dir: Directory from which archiving starts (default: current)
        overwrite: Whether to overwrite existing archive file (default: True)
    """
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

    if not overwrite:
        ext_map = {
            "zip": ".zip",
            "tar": ".tar",
            "gztar": ".tar.gz",
            "bztar": ".tar.bz2",
            "xztar": ".tar.xz",
        }
        ext = ext_map.get(format.lower(), f".{format}")
        expected_file = Path(f"{base_path}{ext}")
        if expected_file.exists():
            raise ValueError(
                f"Archive file '{expected_file}' already exists. "
                f"Set overwrite=True to replace."
            )

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
    overwrite: bool = True,
) -> list[TextContent]:
    """Unpack an archive file with zip-slip safety inspection and overwrite protection.

    Args:
        filename: Path to the archive
        extract_dir: Directory to extract into (default: current)
        format: Archive format (optional)
        overwrite: Whether to overwrite existing files (default: True)
    """
    archive_file = validate_path(filename)
    if extract_dir:
        e_dir = validate_dir_path(extract_dir, create_if_missing=True)
    elif mcp.jail_path:
        e_dir = mcp.jail_path.resolve()
    else:
        e_dir = Path(".").resolve()

    e_dir = validate_path_in_jail(e_dir)

    loop = asyncio.get_running_loop()

    def _check_safety() -> None:
        validate_archive_safety(archive_file, e_dir, format=format)

    await loop.run_in_executor(None, _check_safety)

    await aioshutil.unpack_archive(
        str(archive_file), extract_dir=str(e_dir), format=format
    )

    return json.dumps(
        {
            "operation": "unpack_archive",
            "archive_file": str(archive_file),
            "extract_dir": str(e_dir),
            "verified": True,
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
