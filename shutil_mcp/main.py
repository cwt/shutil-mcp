"""MCP server entry point.

This module serves as the main entry point for the shutil-mcp MCP server.
All tools are imported from their respective module files.
"""

import argparse
import sys

# Import the MCP server instance
from shutil_mcp.server import mcp

# Import all tools to register them with the MCP server
from shutil_mcp.tools import (  # noqa: F401
    cat,
    chmod,
    chown,
    cp,
    disk_usage,
    empty_trash,
    gc_trash,
    get_archive_formats,
    glob,
    grep,
    ls,
    make_archive,
    mkdir,
    mv,
    restore,
    rm,
    stat,
    touch,
    tree,
    unpack_archive,
    which,
)


def main() -> None:
    """Main entry point for the MCP server."""
    from shutil_mcp.helpers import setup_event_loop

    setup_event_loop()

    parser = argparse.ArgumentParser(description="Shutil MCP Server")
    parser.add_argument(
        "--transport",
        nargs="+",
        choices=["stdio", "sse", "streamable-http"],
        default=["stdio"],
        help="Transport protocol(s) to use (default: stdio). "
        "Can specify multiple: --transport sse streamable-http",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on for HTTP transports (default: 8000)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to for HTTP transports (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Require API key authentication. Clients must send "
        "'X-API-Key' or 'API-Key' header with this value.",
    )
    parser.add_argument(
        "--jail",
        default=None,
        required=False,
        help="Restrict file system access to this directory tree. "
        "Required for HTTP transports. Optional for stdio. "
        "Example: --jail /home/user/projects",
    )

    args = parser.parse_args()

    transports = set(args.transport)

    # Jail is required for HTTP transports
    if transports != {"stdio"} and not args.jail:
        print(
            "Error: --jail is required for HTTP transports "
            "(sse, streamable-http).\n"
            "This restricts file system access to a specific directory tree "
            "for security.\n"
            "Example: --jail /home/user/projects",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        if transports == {"stdio"}:
            if args.jail:
                mcp.jail_path = args.jail
                print(f"Jail path set to: {args.jail}", file=sys.stderr)
            mcp.run(transport="stdio")
        elif "stdio" in transports:
            print("Error: Cannot mix stdio with HTTP transports", file=sys.stderr)
            sys.exit(1)
        elif transports.issubset({"sse", "streamable-http"}):
            import uvicorn
            from starlette.applications import Starlette
            from starlette.middleware.cors import CORSMiddleware
            from starlette.routing import BaseRoute, Route

            from shutil_mcp.helpers import APIKeyMiddleware

            mcp.jail_path = args.jail
            if hasattr(mcp.settings, "json_response"):
                mcp.settings.json_response = True

            sse_path = getattr(mcp.settings, "sse_path", "/sse")
            streamable_http_path = getattr(mcp.settings, "streamable_http_path", "/mcp")

            # SSE and Streamable HTTP app setup
            # We must create these apps before Starlette() to use their routes
            sse_app = mcp.sse_app()
            try:
                http_app = mcp.streamable_http_app(json_response=True)
            except TypeError:
                http_app = mcp.streamable_http_app()

            # Create combined routes with proper deduplication
            combined_routes: list[BaseRoute] = []
            added_routes: set[tuple[str, tuple[str, ...]]] = set()

            def _route_key(route: Route) -> tuple[str, tuple[str, ...]]:
                methods = tuple(sorted(route.methods or ["GET"]))
                return (route.path, methods)

            for app_routes in [
                sse_app.routes if "sse" in transports else [],
                http_app.routes if "streamable-http" in transports else [],
            ]:
                for route in app_routes:
                    if isinstance(route, Route):
                        key = _route_key(route)
                        if key not in added_routes:
                            combined_routes.append(route)
                            added_routes.add(key)
                    else:
                        combined_routes.append(route)

            # Combine lifespan contexts when both transports are active
            sse_lifespan = sse_app.router.lifespan_context
            http_lifespan = http_app.router.lifespan_context

            from typing import Any

            lifespan: Any
            if "streamable-http" in transports and "sse" in transports:
                from collections.abc import AsyncIterator
                from contextlib import asynccontextmanager

                @asynccontextmanager
                async def _combined_lifespan(
                    app: Starlette,
                ) -> AsyncIterator[None]:
                    async with sse_lifespan(app):
                        async with http_lifespan(app):
                            yield

                lifespan = _combined_lifespan
            elif "streamable-http" in transports:
                lifespan = http_lifespan
            else:
                lifespan = sse_lifespan

            # Create the Starlette app with combined routes and appropriate lifespan
            app = Starlette(routes=combined_routes, lifespan=lifespan)

            # Add CORS middleware
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["Mcp-Session-Id"],
            )

            # Add API key middleware if needed
            if args.api_key:
                app.add_middleware(APIKeyMiddleware, api_key=args.api_key)
                print("API key authentication enabled")

            print(
                f"Starting Shutil MCP Server with {' and '.join(transports)} transport"
            )
            if "sse" in transports:
                print(f"SSE endpoint: http://{args.host}:{args.port}{sse_path}")
            if "streamable-http" in transports:
                print(
                    f"Streamable HTTP endpoint: http://{args.host}:{args.port}{streamable_http_path}"
                )

            uvicorn.run(app, host=args.host, port=args.port)
        else:
            print(
                f"Error: Invalid transport combination: {transports}",
                file=sys.stderr,
            )
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nServer stopped", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
