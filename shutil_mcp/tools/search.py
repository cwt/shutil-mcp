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

    def _is_binary(filepath: Path) -> bool:
        try:
            with open(filepath, "rb") as f:
                chunk = f.read(1024)
                return b"\x00" in chunk
        except Exception:
            return False

    def _grep() -> list[dict[str, object]]:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            compiled = re.compile(pattern, flags)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        matches: list[dict[str, object]] = []

        def _search_file(filepath: Path) -> None:
            if _is_binary(filepath):
                return
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
                pass

        if root.is_file():
            _search_file(root)
        else:
            for p in root.rglob("*"):
                if len(matches) >= max_results:
                    break
                if p.is_file() and not p.is_symlink():
                    if include and not p.match(include):
                        continue
                    _search_file(p)

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


@mcp.tool()
@handle_errors
@json_tool
async def tree(
    path: str = ".",
    max_depth: int | None = None,
) -> list[TextContent]:
    """Get a recursive directory tree as nested JSON.

    Args:
        path: Root directory to start from (default: '.')
        max_depth: Maximum depth to traverse (default: None = unlimited)
    """
    root = validate_dir_path(path)

    def _build_tree(
        dir_path: Path,
        depth: int = 0,
        visited: set[tuple[int, int]] | None = None,
    ) -> dict[str, object]:
        cur_visited = set() if visited is None else visited
        try:
            st = dir_path.stat()
            dev_ino = (st.st_dev, st.st_ino)
            if dev_ino in cur_visited:
                return {
                    "name": dir_path.name,
                    "type": "directory",
                    "cyclic": True,
                }
            cur_visited.add(dev_ino)
        except Exception:
            pass

        if max_depth is not None and depth > max_depth:
            return {
                "name": dir_path.name,
                "type": "directory",
                "truncated": True,
            }

        def _is_real_dir(p: Path) -> bool:
            return not p.is_symlink() and p.is_dir()

        def _sort_key(p: Path) -> tuple[bool, str]:
            return (not _is_real_dir(p), p.name)

        entries: list[dict[str, object]] = []
        try:
            for entry in sorted(dir_path.iterdir(), key=_sort_key):
                try:
                    is_symlink = entry.is_symlink()
                    is_dir = not is_symlink and entry.is_dir()
                except Exception:
                    continue

                if is_dir:
                    entries.append(
                        _build_tree(entry, depth + 1, set(cur_visited))
                    )
                else:
                    e: dict[str, object] = {
                        "name": entry.name,
                        "type": "symlink" if is_symlink else "file",
                    }
                    try:
                        e["size"] = entry.stat(follow_symlinks=False).st_size
                    except Exception:
                        pass
                    entries.append(e)
        except PermissionError:
            return {
                "name": dir_path.name,
                "type": "directory",
                "error": "permission_denied",
            }

        return {
            "name": dir_path.name,
            "type": "directory",
            "children": entries,
        }

    def _run_tree_build() -> dict[str, object]:
        return _build_tree(root)

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _run_tree_build)

    return json.dumps(
        {
            "operation": "tree",
            "root": str(root),
            "tree": result,
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]
