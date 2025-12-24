# prun-mcp

MCP server for [Prosperous Universe](https://prosperousuniverse.com/) game data via the FIO API.

## Overview

This is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides tools for accessing Prosperous Universe game data. It uses the [FIO REST API](https://rest.fnar.net) to fetch live game information.

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone the repository
git clone <repo-url>
cd prun-mcp

# Install dependencies
uv sync
```

## Usage

### Local

```bash
uv run prun-mcp
```

### Docker

```bash
# Build the image
docker build -t prun-mcp .

# Run with STDIO transport
docker run -i prun-mcp
```

### Claude Code Configuration

**Add the server (local):**
```bash
claude mcp add prun-mcp -- uv run --directory /path/to/prun-mcp prun-mcp
```

**Add the server (Docker):**
```bash
claude mcp add prun-mcp -- docker run -i prun-mcp
```

**Management commands:**
```bash
claude mcp list                # List configured servers
claude mcp remove prun-mcp     # Remove the server
```

### Manual Configuration

Alternatively, add to your MCP client configuration (`~/.claude.json`):

```json
{
  "mcpServers": {
    "prun-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/prun-mcp", "prun-mcp"]
    }
  }
}
```

Or with Docker:

```json
{
  "mcpServers": {
    "prun-mcp": {
      "command": "docker",
      "args": ["run", "-i", "prun-mcp"]
    }
  }
}
```

## Available Tools

### Materials

| Tool | Description |
|------|-------------|
| `get_material_info` | Get information about a material by its ticker symbol (e.g., "BSE", "RAT", "H2O") |

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD="" uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run pyright
```

## Project Structure

```
src/prun_mcp/
├── __init__.py
├── app.py              # FastMCP instance
├── server.py           # Entry point
├── fio/
│   ├── __init__.py
│   ├── client.py       # HTTP client for FIO API
│   └── exceptions.py   # Custom exceptions
└── tools/
    ├── __init__.py
    └── materials.py    # Material-related tools
```

## License

MIT
