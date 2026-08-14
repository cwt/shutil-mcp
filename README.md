# shutil-mcp

An MCP server providing asynchronous shell utilities using `aioshutil`.

This project offers a set of file system tools designed for AI agents,
returning structured JSON output instead of raw text. This allows for more
precise and direct consumption of file system data by AI models.

## Features

- **Asynchronous Operations**: Leverages `aioshutil` and thread executors
  for non-blocking file system tasks.
- **JSON Output**: All tools return minified JSON, optimized for AI agents.
- **Jail Support**: Restrict file system access to a specific directory tree
  for security.
- **Verification & Integrity**: `mv` and `cp` verify destination data before
  unlinking or finalizing, preventing data loss on partial failures.
- **Reversible Mutations & Undo**: `chmod` and `chown` return previous modes
  and ownership to facilitate immediate undo/redo, with automatic rollback
  on failure.
- **Soft-Deletion & Recovery**: `rm` supports `trash=True` soft-deletion with
  a matching `restore` tool.
- **Zip-Slip Protection**: `unpack_archive` validates all archive member paths
  against directory traversal / zip-slip attacks.
- **Detailed Metadata**: Tools like `ls` and `stat` provide comprehensive
  information (size, mtime, mode, owner, etc.).
- **HTTP Transport Support**: Includes built-in support for SSE and Streamable
  HTTP transports.

## Available Tools

- `ls`: List directory contents with detailed metadata.
- `cp`: Copy files or directories recursively with verification.
- `mv`: Move/rename files or directories with safe pre-removal verification.
- `rm`: Remove files or directories (supports `trash=True` soft-deletion).
- `restore`: Restore files or directories from trash.
- `chmod`: Change file/directory permissions with rollback and previous mode.
- `chown`: Change file/directory ownership with rollback and previous owner.
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

```bash
pip install shutil-mcp
```

## Usage

### Run with stdio transport

```bash
shutil-mcp --transport stdio
```

### Run with jail restriction

```bash
shutil-mcp --transport stdio --jail /path/to/projects
```

### Run as SSE server

```bash
shutil-mcp --transport sse --jail /path/to/projects --port 8000
```

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development instructions.

## License

MIT
