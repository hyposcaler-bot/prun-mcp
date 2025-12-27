# prun-mcp

MCP server for [Prosperous Universe](https://prosperousuniverse.com/) game data via the FIO API.

## Overview

This is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides tools for accessing Prosperous Universe game data. It uses the [FIO REST API](https://rest.fnar.net) to fetch live game information.

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone the repository (includes submodules)
git clone --recurse-submodules <repo-url>
cd prun-mcp

# Or if already cloned without submodules:
git submodule update --init

# Install dependencies
uv sync
```

> **Note:** This MCP Server uses content from [fnar/prun-community-derived-mechanics](https://gitlab.com/fnar/prun-community-derived-mechanics) as a git submodule for game mechanics formulas.

### Note on toon-format

This project uses [toon-python](https://github.com/toon-format/toon-python) for TOON serialization (30-60% token reduction vs JSON). The library is installed directly from GitHub because the PyPI version (v0.1.0) has an unimplemented encoder. This is configured in `pyproject.toml` via `[tool.uv.sources]`.

## Usage

### Local

```bash
uv run prun-mcp
```

### Docker

```bash
# Build the image
docker build -t prun-mcp:latest .

# Run with STDIO transport
docker run -i prun-mcp:latest
```

### Claude Code Configuration

**Add the server (local):**
```bash
claude mcp add prun-mcp -- uv run --directory /path/to/prun-mcp prun-mcp
```

**Add the server (Docker):**
```bash
claude mcp add prun-mcp -- docker run -i prun-mcp:latest
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
      "args": ["run", "-i", "prun-mcp:latest"]
    }
  }
}
```

## Available Tools

| Category | Tools | Documentation |
|----------|-------|---------------|
| Materials | `get_material_info`, `refresh_materials_cache`, `get_all_materials` | [docs/tools/materials.md](docs/tools/materials.md) |
| Buildings | `get_building_info`, `refresh_buildings_cache`, `search_buildings` | [docs/tools/buildings.md](docs/tools/buildings.md) |
| Planets | `get_planet_info`, `search_planets` | [docs/tools/planets.md](docs/tools/planets.md) |
| Recipes | `get_recipe_info`, `search_recipes`, `refresh_recipes_cache` | [docs/tools/recipes.md](docs/tools/recipes.md) |
| Exchange | `get_exchange_prices`, `get_exchange_all` | [docs/tools/exchange.md](docs/tools/exchange.md) |
| Market Analysis | `get_market_summary`, `analyze_fill_cost`, `get_price_history_summary`, `get_order_book_depth`, `get_price_history` | [docs/tools/market_analysis.md](docs/tools/market_analysis.md) |
| COGM | `calculate_cogm` | [docs/tools/cogm.md](docs/tools/cogm.md) |
| Permit I/O | `calculate_permit_io`, `calculate_building_cost` | [docs/tools/permit_io.md](docs/tools/permit_io.md) |
| Base Plans | `save_base_plan`, `get_base_plan`, `list_base_plans`, `delete_base_plan`, `calculate_plan_io` | [docs/design/base_plan_memory.md](docs/design/base_plan_memory.md) |

## Available Resources

| URI | Description |
|-----|-------------|
| `exchange://list` | List all commodity exchanges with codes and names |
| `workforce://types` | List workforce types in tier order (Pioneers → Scientists) |
| `workforce://habitation` | List habitation buildings with workforce capacities |
| `buildings://efficiency` | Building efficiency formula and factors overview |
| `buildings://efficiency/workforce` | Workforce satisfaction impact on efficiency |
| `buildings://efficiency/experts` | Expert bonus system (up to ~28.4%) |
| `buildings://efficiency/cogc` | CoGC ADVERTISING program bonuses (up to 25%) |
| `buildings://efficiency/condition` | Building condition and maintenance |
| `pct-mechanics://list` | List of available game mechanics topics |
| `pct-mechanics://arc` | ARC level formula |
| `pct-mechanics://building-degradation` | Building condition and repair cost formulas |
| `pct-mechanics://hq` | HQ upgrade costs and efficiency formula |
| `pct-mechanics://planet` | Planet resource extraction formulas |
| `pct-mechanics://population-infrastructure` | Population needs, happiness, and growth |
| `pct-mechanics://ship-blueprints` | Ship construction formulas and component volumes |
| `pct-mechanics://workforce` | Workforce efficiency formulas |

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `PRUN_MCP_CACHE_DIR` | Directory for cache files (materials, buildings, recipes) | `cache` (relative to working directory) |

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
prun-mcp/
├── data/
│   └── community-mechanics/  # Git submodule: FNAR community-derived game mechanics
├── src/prun_mcp/
│   ├── __init__.py
│   ├── app.py              # FastMCP instance
│   ├── server.py           # Entry point
│   ├── fio/
│   │   ├── __init__.py
│   │   ├── client.py       # HTTP client for FIO API
│   │   └── exceptions.py   # Custom exceptions
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── materials_cache.py  # Materials cache (JSON-based, 24h TTL)
│   │   ├── buildings_cache.py  # Buildings cache (JSON-based, 24h TTL)
│   │   ├── recipes_cache.py    # Recipes cache (JSON-based, 24h TTL)
│   │   └── workforce_cache.py  # Workforce needs cache (JSON-based, 24h TTL)
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base_plan_storage.py  # Base plan persistent storage
│   │   └── validation.py         # Plan validation rules
│   ├── resources/
│   │   ├── __init__.py
│   │   ├── buildings.py    # Building efficiency documentation
│   │   ├── exchanges.py    # Exchange data resource
│   │   ├── extraction.py   # Extraction building constants (EXT, RIG, COL)
│   │   ├── mechanics.py    # Community mechanics resources
│   │   └── workforce.py    # Workforce types and habitation resource
│   └── tools/
│       ├── __init__.py
│       ├── materials.py        # Material-related tools
│       ├── buildings.py        # Building-related tools
│       ├── planets.py          # Planet-related tools (no cache)
│       ├── recipes.py          # Recipe-related tools
│       ├── exchange.py         # Exchange/pricing tools (no cache)
│       ├── market_analysis.py  # Market analysis tools (no cache)
│       ├── cogm.py             # COGM calculation tool
│       ├── permit_io.py        # Permit I/O calculation tool
│       └── base_plans.py       # Base plan management tools
```

## License

MIT
