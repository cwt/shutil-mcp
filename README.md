# shutil-mcp

An MCP server providing asynchronous shell utilities using `aioshutil`.

This project offers a set of file system tools designed for AI agents, returning structured JSON output instead of raw text. This allows for more precise and direct consumption of file system data by AI models.

## Features

- **Asynchronous Operations**: Leverages `aioshutil` for non-blocking file system tasks.
- **JSON Output**: All tools return minified JSON, optimized for AI agents.
- **Jail Support**: Restrict file system access to a specific directory tree for security.
- **Detailed Metadata**: Tools like `ls` provide comprehensive information (size, mtime, mode, owner, etc.).
- **HTTP Transport Support**: Includes built-in support for SSE and Streamable HTTP transports.

## Available Tools

- `ls`: List directory contents with detailed metadata.
- `cp`: Copy files or directories recursively.
- `mv`: Move/rename files or directories.
- `rm`: Remove files or directories recursively.
- `chmod`: Change file/directory permissions.
- `chown`: Change file/directory ownership.
- `disk_usage`: Get disk usage statistics for a path.
- `which`: Find the path to an executable.
- `cat`: Read file content, optionally limited to a specific line range.
- `make_archive`: Create archive files (zip, tar, etc.).
- `unpack_archive`: Unpack archive files.
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

See [@DEVELOPMENT.md](@DEVELOPMENT.md) for detailed development instructions.

## License

MIT
