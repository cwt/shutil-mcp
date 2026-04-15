"""Helper functions for the shutil-mcp MCP server.

Provides common utilities for path validation, formatting, and performance setup.
"""

import json
import secrets
from pathlib import Path
from typing import Any, Awaitable, Callable


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
        path: The absolute path to validate.

    Returns:
        The resolved absolute Path object.

    Raises:
        ValueError: If jail is set and path is outside it.
    """
    from shutil_mcp.server import mcp

    if mcp.jail_path is None:
        return path

    # We use resolve() to handle '..' and symlinks for security
    try:
        resolved = path.resolve()
        # If path doesn't exist, resolve() might not resolve '..' properly on all systems
        # but absolute() + normalpath is a good fallback.
        # For security, we really want existing paths to be resolved.
    except Exception:
        resolved = path.absolute()

    try:
        resolved.relative_to(mcp.jail_path)
    except ValueError:
        # Fallback check for cases where relative_to fails but it's actually inside
        if str(resolved).startswith(str(mcp.jail_path)):
            return resolved
        raise ValueError(
            f"Path '{resolved}' is outside the allowed jail directory '{mcp.jail_path}'. "
            f"Access is restricted to '{mcp.jail_path}' and its subdirectories."
        )

    return resolved


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


def format_bytes(size: int) -> str:
    """Format bytes into a human-readable string (e.g., '1.5 MB')."""
    current_size: float = float(size)
    for unit in ["bytes", "KB", "MB", "GB", "TB"]:
        if current_size < 1024:
            if unit == "bytes":
                return f"{int(current_size)} {unit}"
            return f"{current_size:.2f} {unit}"
        current_size /= 1024
    return f"{current_size:.2f} PB"


def validate_path(path_str: str, must_exist: bool = True) -> Path:
    """Validate that path_str is a safe path.

    Args:
        path_str: The path to validate.
        must_exist: If True, raise ValueError if path doesn't exist.

    Returns:
        The resolved absolute Path object.

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

    if must_exist and not path.exists():
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


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """Sanitize user-provided input.

    Args:
        value: The input string to sanitize
        max_length: Maximum allowed length (default 1000)

    Returns:
        The sanitized string
    """
    if not value:
        return value

    if len(value) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length}")

    # Reject whitespace-only input
    if not value.strip():
        raise ValueError("Input must not be empty or whitespace-only")

    return value
