"""Decorators for MCP tools.

Provides @json_tool and @handle_errors decorators for consistent
tool output handling and error management.
"""

import functools
from collections.abc import Awaitable, Callable

from mcp.types import Annotations, TextContent


def json_tool(
    func: Callable[..., Awaitable[list[TextContent] | str]],
) -> Callable[..., Awaitable[list[TextContent]]]:
    """Decorator for tools that return JSON output.

    Wraps the returned JSON string in TextContent with audience: ["assistant"]
    annotation to indicate this content is intended for AI agents (minified,
    machine-readable) rather than human users.

    The decorated function should return a string (JSON output) or list[TextContent].
    """

    @functools.wraps(func)
    async def wrapper(  # type: ignore[no-untyped-def]
        *args, **kwargs
    ) -> list[TextContent]:
        result = await func(*args, **kwargs)

        # If result is an error (str type), return as plain text in TextContent
        # (users should see errors)
        if isinstance(result, str) and result.startswith("Error"):
            return [
                TextContent(
                    type="text",
                    text=result,
                    annotations=Annotations(audience=["user"], priority=1.0),
                )
            ]

        # If result is already list[TextContent], return as-is
        if isinstance(result, list):
            return result

        # Wrap JSON output (str) in TextContent with assistant-only annotation
        return [
            TextContent(
                type="text",
                text=result,
                annotations=Annotations(audience=["assistant"], priority=0.5),
            )
        ]

    wrapper._is_json_tool = True  # type: ignore[attr-defined]  # Marker for handle_errors detection
    return wrapper


def handle_errors(
    func: Callable[..., Awaitable[str | list[TextContent]]],
) -> Callable[..., Awaitable[str | list[TextContent]]]:
    """Decorator to handle common validation errors.

    For functions decorated with @json_tool, returns errors as list[TextContent]
    with audience=['user'] to ensure errors are visible to users.
    For other functions, returns errors as plain str.
    """
    from mcp.types import Annotations as AnnotationsType

    @functools.wraps(func)
    async def wrapper(  # type: ignore[no-untyped-def]
        *args, **kwargs
    ) -> str | list[TextContent]:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_msg = f"Error: {e}"

            # Check if the wrapped function is decorated with @json_tool
            # by looking for the _is_json_tool marker attribute
            is_json_tool = getattr(func, "_is_json_tool", False)

            if is_json_tool:
                return [
                    TextContent(
                        type="text",
                        text=error_msg,
                        annotations=AnnotationsType(
                            audience=["user"], priority=1.0
                        ),
                    )
                ]
            return error_msg

    return wrapper
