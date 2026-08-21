"""Helper functions for the shutil-mcp MCP server.

Provides common utilities for path validation and performance setup.
"""

import json
import os
import secrets
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, cast


class APIKeyMiddleware:
    """ASGI Middleware that validates API key from request headers."""

    def __init__(self, app: Any, api_key: str) -> None:
        self.app = app
        self.api_key = api_key

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip auth for CORS preflight
        if scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # Check API key from headers
        headers = dict(scope.get("headers", []))
        provided_key_bytes = headers.get(b"x-api-key") or headers.get(
            b"api-key"
        )

        is_authorized = False
        if provided_key_bytes:
            try:
                provided_key = provided_key_bytes.decode("latin-1")
                if secrets.compare_digest(provided_key, self.api_key):
                    is_authorized = True
            except Exception:
                pass

        if is_authorized:
            await self.app(scope, receive, send)
            return

        # Unauthorized response
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps(
                    {"error": "Unauthorized: Invalid or missing API key"}
                ).encode("utf-8"),
            }
        )


def validate_path_in_jail(path: Path) -> Path:
    """Validate that a path is within the jail directory.

    Args:
        path: The path to validate.

    Returns:
        The validated Path object.

    Raises:
        ValueError: If jail is set and path is outside it.
    """
    from shutil_mcp.server import mcp

    if mcp.jail_path is None:
        return path

    jail = mcp.jail_path.resolve()

    try:
        resolved = path.resolve()
    except Exception:
        # Fallback: use realpath which always follows symlinks
        import os

        resolved = Path(os.path.realpath(str(path)))

    try:
        resolved.relative_to(jail)
    except ValueError:
        raise ValueError(
            f"Path '{path}' (resolved: '{resolved}') is outside the "
            f"allowed jail directory '{jail}'. "
            f"Access is restricted to '{jail}' and its subdirectories."
        )

    return path


def setup_event_loop() -> None:
    """Set up uvloop (Unix) or winloop (Windows) for better performance if available."""
    import sys

    if sys.platform == "win32":
        try:
            import winloop  # type: ignore[import-not-found]

            winloop.install()
        except ImportError:
            pass
    else:
        try:
            import uvloop

            uvloop.install()
        except ImportError:
            pass


def validate_path(path_str: str, must_exist: bool = True) -> Path:
    """Validate that path_str is a safe path.

    Args:
        path_str: The path to validate.
        must_exist: If True, raise ValueError if path doesn't exist.

    Returns:
        The validated Path object.

    Raises:
        ValueError: If the path is invalid or outside jail.
    """
    try:
        p_str = path_str.strip() if path_str and path_str.strip() else "."
        path = Path(p_str).absolute()
    except Exception as e:
        raise ValueError(f"Invalid path format: {e}") from e

    # Check jail restriction
    path = validate_path_in_jail(path)

    if must_exist and not (path.exists() or path.is_symlink()):
        raise ValueError(f"Path does not exist: {path}")

    return path


def validate_dir_path(path_str: str, create_if_missing: bool = False) -> Path:
    """Validate that path_str is a safe directory path.

    Args:
        path_str: The path to validate.
        create_if_missing: If True, create the directory if it doesn't exist.

    Returns:
        The resolved absolute Path object.

    Raises:
        ValueError: If the path is invalid, is not a directory, or outside jail.
    """
    path = validate_path(path_str, must_exist=not create_if_missing)

    if not path.exists():
        if create_if_missing:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Failed to create directory {path}: {e}")
    elif not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    return path


def get_trash_dir(path: Path) -> Path:
    """Get and create a trash directory for soft deletions.

    If a jail is configured, uses .trash inside the jail root.
    Otherwise, uses .trash in the path's parent directory.
    """
    from shutil_mcp.server import mcp

    if mcp.jail_path is not None:
        trash_dir = mcp.jail_path.resolve() / ".trash"
    else:
        trash_dir = path.parent.resolve() / ".trash"

    trash_dir = validate_path_in_jail(trash_dir)
    trash_dir.mkdir(parents=True, exist_ok=True)
    return trash_dir


TRASH_META_DIRNAME = ".meta"


def get_dir_size(path: Path) -> int:
    """Return total size in bytes of all regular files under ``path``.

    Symlinks are not followed, so their targets are not counted (this avoids
    double-counting and symlink loops).
    """
    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as scandir_it:
                for entry in scandir_it:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        else:
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def write_trash_meta(
    trash_dir: Path, item_name: str, original_path: str, trashed_at: int
) -> None:
    """Persist metadata (original path + deletion time) for a trashed item."""
    meta_dir = trash_dir / TRASH_META_DIRNAME
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta_path = meta_dir / f"{item_name}.json"
    meta = {"original_path": original_path, "trashed_at": trashed_at}
    meta_path.write_text(json.dumps(meta), encoding="utf-8")


def read_trash_meta(trash_dir: Path, item_name: str) -> dict[str, object]:
    """Read metadata for a trashed item, returning ``{}`` if unavailable."""
    meta_path = trash_dir / TRASH_META_DIRNAME / f"{item_name}.json"
    try:
        raw = meta_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def build_trash_report(trash_dir: Path) -> dict[str, object]:
    """Build a report describing trash size, storage share, and contents.

    The report contains:
      - ``path``: the trash directory
      - ``item_count``: number of trashed items
      - ``total_bytes``: sum of trashed item sizes
      - ``storage``: total/used/free bytes plus ``trash_bytes`` and
        ``trash_used_percent`` (share of total storage occupied by trash)
      - ``contents``: list of ``{name, original_path, trashed_at, size_bytes}``
    """
    trash_dir = validate_path_in_jail(trash_dir)

    contents: list[dict[str, object]] = []
    try:
        with os.scandir(trash_dir) as scandir_it:
            for entry in scandir_it:
                if entry.name == TRASH_META_DIRNAME:
                    continue
                item_path = Path(entry.path)
                if entry.is_symlink():
                    size = 0
                elif entry.is_dir(follow_symlinks=False):
                    size = get_dir_size(item_path)
                else:
                    try:
                        size = entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        size = 0
                meta = read_trash_meta(trash_dir, entry.name)
                contents.append(
                    {
                        "name": entry.name,
                        "original_path": meta.get("original_path", entry.name),
                        "trashed_at": meta.get("trashed_at", 0),
                        "size_bytes": size,
                    }
                )
    except OSError:
        pass

    contents.sort(key=lambda c: cast(int, c["trashed_at"]))

    total_bytes = sum(cast(int, c["size_bytes"]) for c in contents)
    usage = shutil.disk_usage(str(trash_dir))
    trash_used_percent = (
        round((total_bytes / usage.total) * 100, 4) if usage.total > 0 else 0.0
    )

    return {
        "path": str(trash_dir),
        "item_count": len(contents),
        "total_bytes": total_bytes,
        "storage": {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "trash_bytes": total_bytes,
            "trash_used_percent": trash_used_percent,
        },
        "contents": contents,
    }


def validate_archive_safety(
    archive_path: Path,
    extract_dir: Path,
    format: str | None = None,
) -> None:
    """Validate that an archive contains no zip-slip or path traversal attacks.

    Args:
        archive_path: Path to the archive file.
        extract_dir: Path to directory where files will be extracted.
        format: Optional archive format.

    Raises:
        ValueError: If any member path escapes extract_dir or jail.
    """
    resolved_extract_dir = extract_dir.resolve()
    fmt = (format or "").lower()
    path_str = str(archive_path).lower()

    import tarfile
    import zipfile

    if fmt == "zip" or path_str.endswith((".zip", ".cbz")):
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zf:
                for name in zf.namelist():
                    if name.startswith("/") or name.startswith("\\"):
                        raise ValueError(
                            f"Unsafe absolute path in archive member: '{name}'"
                        )
                    target = (resolved_extract_dir / name).resolve()
                    try:
                        target.relative_to(resolved_extract_dir)
                        validate_path_in_jail(target)
                    except ValueError as e:
                        raise ValueError(
                            f"Unsafe archive member path escaping destination: '{name}'"
                        ) from e
    elif tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, "r:*") as tf:
            for member in tf.getmembers():
                if member.name.startswith("/") or member.name.startswith("\\"):
                    raise ValueError(
                        f"Unsafe absolute path in archive member: '{member.name}'"
                    )
                if member.islnk() or member.issym():
                    link_target = member.linkname
                    if link_target.startswith("/") or link_target.startswith(
                        "\\"
                    ):
                        raise ValueError(
                            f"Unsafe absolute symlink in archive member: '{member.name}' -> '{link_target}'"
                        )
                target = (resolved_extract_dir / member.name).resolve()
                try:
                    target.relative_to(resolved_extract_dir)
                    validate_path_in_jail(target)
                except ValueError as e:
                    raise ValueError(
                        f"Unsafe archive member path escaping destination: '{member.name}'"
                    ) from e
