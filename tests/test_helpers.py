import json
from pathlib import Path
from typing import Any

import pytest

from shutil_mcp.helpers import (
    APIKeyMiddleware,
    is_trash_path,
    sanitize_trash_name,
    setup_event_loop,
    validate_dir_path,
)


@pytest.mark.asyncio
async def test_api_key_middleware() -> None:
    async def dummy_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b'{"status":"ok"}',
            }
        )

    middleware = APIKeyMiddleware(dummy_app, api_key="secret-123")

    # 1. Non-http scope passes through
    non_http_received = False

    async def non_http_app(
        scope: dict[str, Any], receive: Any, send: Any
    ) -> None:
        nonlocal non_http_received
        non_http_received = True

    non_http_middleware = APIKeyMiddleware(non_http_app, api_key="secret-123")
    await non_http_middleware({"type": "websocket"}, None, None)  # type: ignore[arg-type]
    assert non_http_received is True

    # 2. OPTIONS method skips auth (CORS preflight)
    options_responses: list[dict[str, Any]] = []

    async def send_options(msg: dict[str, Any]) -> None:
        options_responses.append(msg)

    await middleware(
        {"type": "http", "method": "OPTIONS", "headers": []},
        None,  # type: ignore[arg-type]
        send_options,
    )
    assert options_responses[0]["status"] == 200

    # 3. Missing API key returns 401
    unauthorized_responses: list[dict[str, Any]] = []

    async def send_unauthorized(msg: dict[str, Any]) -> None:
        unauthorized_responses.append(msg)

    await middleware(
        {"type": "http", "method": "GET", "headers": []},
        None,  # type: ignore[arg-type]
        send_unauthorized,
    )
    assert unauthorized_responses[0]["status"] == 401
    body = json.loads(unauthorized_responses[1]["body"].decode("utf-8"))
    assert "Unauthorized" in body["error"]

    # 4. Invalid API key returns 401
    invalid_responses: list[dict[str, Any]] = []

    async def send_invalid(msg: dict[str, Any]) -> None:
        invalid_responses.append(msg)

    await middleware(
        {
            "type": "http",
            "method": "GET",
            "headers": [(b"x-api-key", b"wrong-key")],
        },
        None,  # type: ignore[arg-type]
        send_invalid,
    )
    assert invalid_responses[0]["status"] == 401

    # 5. Valid API key passes through
    authorized_responses: list[dict[str, Any]] = []

    async def send_authorized(msg: dict[str, Any]) -> None:
        authorized_responses.append(msg)

    await middleware(
        {
            "type": "http",
            "method": "GET",
            "headers": [(b"x-api-key", b"secret-123")],
        },
        None,  # type: ignore[arg-type]
        send_authorized,
    )
    assert authorized_responses[0]["status"] == 200


def test_setup_event_loop() -> None:
    # Test that setup_event_loop runs without exception
    setup_event_loop()


def test_validate_dir_path(tmp_path: Path) -> None:
    # 1. Existing directory
    d = tmp_path / "existing_dir"
    d.mkdir()
    assert validate_dir_path(str(d)) == d.resolve()

    # 2. File instead of directory
    f = tmp_path / "file.txt"
    f.write_text("hello")
    with pytest.raises(ValueError, match="not a directory"):
        validate_dir_path(str(f))

    # 3. Create if missing
    new_d = tmp_path / "auto_created_dir"
    assert not new_d.exists()
    assert (
        validate_dir_path(str(new_d), create_if_missing=True) == new_d.resolve()
    )
    assert new_d.exists()


def test_sanitize_trash_name_strips_separators() -> None:
    assert sanitize_trash_name("file.txt") == "file.txt"
    assert sanitize_trash_name("../evil.txt") == "evil.txt"
    assert sanitize_trash_name("sub/dir/file.txt") == "sub_dir_file.txt"
    assert sanitize_trash_name("") == "unnamed"
    assert sanitize_trash_name("....") == "unnamed"


def test_is_trash_path() -> None:
    p = Path("/a/.trash/1234_file.txt")
    assert is_trash_path(p) is True

    p2 = Path("/a/b/file.txt")
    assert is_trash_path(p2) is False

    p3 = Path("/a/jail_subdir/file.txt")
    assert is_trash_path(p3) is False
