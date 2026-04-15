# Development Guide for shutil-mcp

This document describes development conventions and best practices for the
shutil-mcp MCP server.

## References

- **FastMCP Documentation**: <https://gofastmcp.com/>
- **aioshutil Documentation**: <https://github.com/vpetrigo/aioshutil>
- **MCP Protocol Documentation**: <https://modelcontextprotocol.info/docs/concepts/tools/>

## MCP Server Architecture

This project uses a custom `SHUTIL_MCP` subclass of `FastMCP` to provide additional functionality:

- **Jail Path Support**: The `jail_path` property allows restricting file system access to a specific directory tree.
- **Immutability**: Once `jail_path` is set to a non-None value, it becomes immutable to prevent runtime configuration changes that could bypass security.
- **Security**: API key validation uses `secrets.compare_digest` to prevent timing attacks.

## Tool Parameter Ordering

**CRITICAL**: All MCP tools should follow this parameter ordering convention:

1. **Required parameters** (without defaults) come FIRST
2. **`path`** (if it has a default like `"."`) comes next
3. **Optional parameters** (with defaults) come last

### Examples

**✓ CORRECT:**

```python
@mcp.tool()
@handle_errors
@json_tool
async def ls(path: str = ".") -> str:
    # Only path - simplest case
    # ...
```

```python
@mcp.tool()
@handle_errors
@json_tool
async def cp(src: str, dst: str, follow_symlinks: bool = True) -> str:
    # src, dst are required - FIRST
    # follow_symlinks is optional - LAST
    # ...
```

## Adding New Tools

When adding a new MCP tool:

1. **Use the `@mcp.tool()` decorator**
2. **Apply `@handle_errors` decorator** for file system operations
3. **Apply `@json_tool` decorator** to return JSON output
4. **Follow parameter ordering**: required params first, then optional params
5. **Validate paths** using `validate_path(path)` or `validate_dir_path(path)`
6. **Ensure all operations are asynchronous** using `aioshutil` or running blocking calls in executors
7. **Return minified JSON** for efficiency

## Code Quality

Before committing changes, always run the following scripts:

```bash
# 1. Run linting and auto-fix issues
./scripts/lint-check-and-fix.sh

# 2. Run type checking
./scripts/type-check.sh

# 3. Format code before final commit
./scripts/code-format.sh
```

## Testing New Tools

Test new tools manually using the MCP client or by calling them directly in a
Python REPL.

**Full test suite (when implemented):**

```bash
./scripts/runtest.sh
```
