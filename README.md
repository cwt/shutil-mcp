# shutil-mcp

[![M8ven Live Monitored](https://m8ven.ai/badge/mcp/cwt-shutil-mcp-1bs6po)](https://m8ven.ai/mcp/cwt-shutil-mcp-1bs6po)

An MCP server providing asynchronous shell utilities using `aioshutil`.

This project offers a set of file system tools designed for AI agents,
returning structured JSON output instead of raw text. This allows for more
precise and direct consumption of file system data by AI models.

## Features

- **Asynchronous Operations**: Leverages `aioshutil` and thread executors
  for non-blocking file system tasks.
- **JSON Output**: All tools return minified JSON, optimized for AI agents.
- **Tool Annotations & Hints**: Declares `readOnlyHint`, `destructiveHint`,
  `idempotentHint`, and `openWorldHint` on every tool for agent safety and host warnings.
- **Jail Support**: Restrict file system access to a specific directory tree
  for security.
- **Verification & Integrity**: `mv` and `cp` verify destination data before
  unlinking or finalizing, preventing data loss on partial failures.
- **Reversible Mutations & Undo**: `chmod` and `chown` return previous modes
  and ownership to facilitate immediate undo/redo, with automatic rollback
  on failure.
- **Safe Deletion & Recovery**: `rm` always soft-deletes into `.trash` (never
  permanently deletes) and reports trash size and storage usage; `restore`
  recovers items, `gc_trash` collects expired items, and `empty_trash` purges the trash.
- **Zip-Slip Protection**: `unpack_archive` validates all archive member paths
  against directory traversal / zip-slip attacks.
- **Detailed Metadata**: Tools like `ls` and `stat` provide comprehensive
  information (size, mtime, mode, owner, etc.).
- **HTTP Transport Support**: Includes built-in support for SSE and Streamable
  HTTP transports.

## Available Tools

- `ls`: List directory contents with detailed metadata.
- `cp`: Copy files or directories recursively with verification and overwrite protection.
- `mv`: Move/rename files or directories with safe pre-removal verification.
- `rm`: Soft-delete by moving to `.trash`; never permanently deletes and reports trash statistics.
- `restore`: Restore files or directories from trash (defaults to original path).
- `empty_trash`: Permanently purge the trash folder (only after explicit user confirmation).
- `gc_trash`: Garbage-collect expired trash entries based on age threshold.
- `mkdir`: Create a new directory.
- `touch`: Create an empty file or update file timestamps.
- `chmod`: Change file/directory permissions with rollback and previous mode.
- `chown`: Change file/directory ownership with rollback and previous owner.
- `stat`: Get detailed file or directory metadata.
- `disk_usage`: Get disk usage statistics for a path.
- `which`: Find the path to an executable.
- `cat`: Read file content, optionally limited to a specific line range.
- `glob`: Find files matching glob patterns.
- `grep`: Search file contents using regex patterns.
- `tree`: Get a recursive directory tree as nested JSON.
- `make_archive`: Create archive files (zip, tar, etc.) with overwrite guards.
- `unpack_archive`: Unpack archive files safely with zip-slip protection.
- `get_archive_formats`: List supported archive formats.

## Installation

### Using Poetry (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd shutil-mcp

# Install dependencies
poetry install

# Optional: Install with performance enhancements (uvloop / winloop)
poetry install --all-extras
```

### Using pip

```bash
# Install from PyPI
pip install shutil-mcp

# Or install in editable mode with speed dependencies
pip install -e ".[speed]"
```

## Usage

### Standard Input/Output (stdio) - Default Mode

```bash
shutil-mcp --transport stdio
```

With jail restriction:

```bash
shutil-mcp --transport stdio --jail /path/to/projects
```

### HTTP Transports (SSE and/or Streamable HTTP)

For web-based MCP clients (such as llama.cpp WebUI), you can run with HTTP transport:

```bash
# SSE only (compatible with llama.cpp WebUI)
shutil-mcp --transport sse --jail /path/to/projects --port 8000

# Streamable HTTP only
shutil-mcp --transport streamable-http --jail /path/to/projects --port 8000

# Both SSE and Streamable HTTP on the same server
shutil-mcp --transport sse streamable-http --jail /path/to/projects --port 8000
```

**Endpoints:**

- SSE: `http://localhost:8000/sse`
- Streamable HTTP: `http://localhost:8000/mcp`

**Options:**

- `--transport`: Transport protocol(s) (`stdio`, `sse`, `streamable-http`, default: `stdio`)
- `--port`: Port to listen on (default: 8000)
- `--host`: Host to bind to (default: 0.0.0.0)
- `--jail`: **Required for HTTP transports.** Restrict file system operations to this directory tree for security.
- `--api-key`: **Optional.** Enable mandatory API key authentication (`X-API-Key` or `API-Key` header).

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development instructions.

### Running Tests

```bash
poetry run pytest -n auto
```

### Code Quality

```bash
# Run linting and auto-fix issues
./scripts/lint-check-and-fix.sh

# Run static type checking (strict mode)
./scripts/type-check.sh

# Run code formatter and trailing whitespace cleanup (cross-platform Linux & macOS)
./scripts/code-format.sh
```

## License

MIT
