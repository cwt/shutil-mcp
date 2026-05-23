"""File search tools.

Provides 'glob' and 'grep' tools for finding files
and searching within file contents.
"""

import asyncio
import json
import re
from pathlib import Path

from mcp.types import TextContent

from shutil_mcp.decorators import handle_errors, json_tool
from shutil_mcp.helpers import validate_dir_path, validate_path
from shutil_mcp.server import mcp


@mcp.tool()
@handle_errors
@json_tool
async def glob(
    pattern: str,
    path: str = ".",
) -> list[TextContent]:
    """Find files matching glob patterns.

    Args:
        pattern: Glob pattern (e.g., '**/*.py', '*.txt', 'src/**/*.ts')
        path: Root directory to search from (default: '.')
    """
    root = validate_dir_path(path)

    def _glob() -> list[str]:
        matched = []
        for p in sorted(root.glob(pattern)):
            matched.append(str(p.relative_to(root)))
        return matched

    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(None, _glob)

    return json.dumps(
        {
            "operation": "glob",
            "pattern": pattern,
            "root": str(root),
            "matches": results,
            "count": len(results),
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def grep(
    pattern: str,
    path: str = ".",
    include: str | None = None,
    case_sensitive: bool = True,
    max_results: int = 100,
) -> list[TextContent]:
    """Search file contents using regex patterns.

    Args:
        pattern: Regex pattern to search for
        path: File or directory to search in (default: '.')
        include: Optional file glob pattern to filter (e.g., '*.py')
        case_sensitive: Whether search is case-sensitive (default: True)
        max_results: Maximum number of matches to return (default: 100)
    """
    root = validate_path(path)

    def _grep() -> list[dict[str, object]]:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            compiled = re.compile(pattern, flags)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        files_to_search: list[Path] = []
        if root.is_file():
            files_to_search = [root]
        else:
            for p in root.rglob("*"):
                if p.is_file() and not p.is_symlink():
                    if include and not p.match(include):
                        continue
                    files_to_search.append(p)

        matches: list[dict[str, object]] = []
        for filepath in files_to_search:
            if len(matches) >= max_results:
                break
            try:
                with open(filepath, encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if len(matches) >= max_results:
                            break
                        if compiled.search(line):
                            matches.append(
                                {
                                    "file": str(filepath),
                                    "line": i,
                                    "content": line.rstrip("\n\r"),
                                }
                            )
            except Exception:
                continue

        return matches

    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(None, _grep)

    return json.dumps(
        {
            "operation": "grep",
            "pattern": pattern,
            "path": str(root),
            "matches": results,
            "count": len(results),
            "truncated": len(results) >= max_results,
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


