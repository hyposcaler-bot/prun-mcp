
# MCP Server for Prosperous Universe

The MCP server is intended to provide in-game info from the game [Prosperous Universe](https://prosperousuniverse.com/)

## Dependencies and Libraries

For package management and virtual environments it will use [astral-sh/uv](https://github.com/astral-sh/uv)
Additional UV information can be found in the [UV documentation](https://docs.astral.sh/uv/)

For handling MCP related details it will use the [ModelContextProtocol Python-SDK](https://github.com/modelcontextprotocol/python-sdk)

For TOON serialization it will use the python library from [toon-format/toon-python](https://github.com/toon-format/toon-python) repository. TOON provides 30-60% token reduction vs JSON through YAML-like syntax for objects and CSV-like tabular format for uniform arrays.

It will rely on the FIO REST API to gather live information from the game, a swagger spec for the API can be found in [./docs/FIO/fio-swagger.json](./docs/FIO/fio-swagger.json)


## Design Principles


### TOON

Details on the TOON spec as well as the API used by the [toon-format/toon-python lib](https://github.com/toon-format/toon-python) can be found in this [README.md](https://github.com/toon-format/toon-python/)

### MCP python-SDK

The following readme [https://github.com/modelcontextprotocol/python-sdk/blob/main/README.md](https://github.com/modelcontextprotocol/python-sdk/blob/main/README.md) 

### Tool Types

The server provides two categories of tools:

1. **Analysis Tools** - Return plain text summaries with conclusions
   - Server-side computation and analysis
   - Minimal context footprint
   - Example: "Best arbitrage: RAT CI1→NC1, 12% margin"

2. **Raw Data Tools** - Return TOON-encoded structured data
   - For LLM-side analysis and reasoning
   - Tabular format ideal for order books, price histories, material lists
   - Always use TOON serialization (no JSON option)

### Response Format

- Analysis tools: Plain text
- Raw data tools: TOON-encoded (tool-level encoding, no middleware)

### Error Handling

MCP distinguishes between two error types ([spec reference](https://modelcontextprotocol.io/specification/2024-11-05/server/tools)):

| Error Type | When | How |
|------------|------|-----|
| **Protocol errors** | Unknown tool, invalid arguments, server crash | JSON-RPC error response (raised exception) |
| **Tool execution errors** | API failures, invalid data, business logic | Return descriptive text content |

**Pattern for handling errors:**

```python
@mcp.tool()
async def get_exchange_prices(ticker: str, exchange: str) -> str | list[TextContent]:
    try:
        data = await client.get_exchange_info(ticker, exchange)
        return toon_encode({"prices": [data]})
    except FIONotFoundError:
        # Not-found is not an error - tool worked, just found nothing
        return [TextContent(type="text", text=f"No exchange data for {ticker}.{exchange}")]
    except FIOApiError as e:
        # API failures return descriptive text
        return [TextContent(type="text", text=f"FIO API error: {e}")]
```

**Design rationale:**
- "Not found" isn't a tool failure - the tool executed correctly, it just found nothing
- Returning descriptive text lets the LLM reason about next steps
- Simpler than constructing `ToolResult` wrappers
- Reserve `isError=True` for catastrophic failures only

**Guidelines:**
- Return `[TextContent(...)]` for expected "not found" cases
- Let exceptions propagate for unexpected failures (network down, server crash)
- Include descriptive messages the LLM can reason about
- Never expose internal stack traces

### Caching Strategy

> **Note**: FIO recommends not caching their API responses as they've optimized with CloudFlare ([source](https://fnar.net/page/projects/)). However, selective caching is still useful for specific cases below.

- **Backend**: JSON files (simple parsing, dict-based data)
- **Structure**: One file per entity type (`materials.json`, `buildings.json`, `recipes.json`)
- **Location**: Configurable via `PRUN_MCP_CACHE_DIR` env var (default: `cache/`)

**What to cache:**

| Data Type | Cache? | Reason | TTL |
|-----------|--------|--------|-----|
| Materials | Yes | Static, rarely changes | 24h or manual |
| Buildings | Yes | Static, rarely changes | 24h or manual |
| Recipes | Yes | Static, rarely changes | 24h or manual |
| Workforce | Yes | Static needs data | 24h or manual |
| Exchange prices | Yes | In-memory cache for market analysis tools | 2.5 min |
| Order books | Yes | In-memory cache (same as exchange prices) | 2.5 min |
| Planet data | No | FIO handles caching, fetched on-demand | - |

**Invalidation**: TTL-based (24h) with manual refresh tools:
- `refresh_materials_cache`
- `refresh_buildings_cache`
- `refresh_recipes_cache`

## Server Configuration

Following MCP Python SDK conventions:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("prun_mcp")
```

## Requirements

> **NOTE**: For STDIO-based servers: Never write to standard output (`stdout`). Writing to stdout will corrupt the JSON-RPC messages and break your server. This includes `print()` statements in Python—by default they write to `stdout`.

Errors and logging must be written to `stderr`.

## Project Structure

```
prun-mcp/
  pyproject.toml
  src/
    prun_mcp/
      __init__.py
      app.py              # FastMCP instance
      server.py           # Entry point with async lifecycle
      fio/                # FIO API client
        __init__.py
        client.py         # httpx AsyncClient wrapper
        exceptions.py     # FIOApiError, FIONotFoundError
      cache/              # JSON-based caching layer (24h TTL)
        __init__.py
        materials_cache.py
        buildings_cache.py
        recipes_cache.py
        workforce_cache.py
      models/             # Pydantic models for type safety
        __init__.py
        fio.py            # FIO API response models
        domain.py         # Domain output models (COGM, BuildingCost, etc.)
      prun_lib/           # Business logic layer
        __init__.py       # Public API exports
        exceptions.py     # Unified exception classes
        building.py       # Building cost calculations
        cogm.py           # COGM calculations
        market.py         # Market analysis logic
        base_io.py        # Base I/O calculations
        exchange.py       # Exchange validation
        ...               # Additional modules
      storage/            # Persistent storage
        __init__.py
        base_plan_storage.py
        validation.py
      resources/          # Static reference data (MCP resources)
        __init__.py
        buildings.py      # Building efficiency documentation
        exchanges.py      # Exchange data resource
        extraction.py     # Extraction building constants
        mechanics.py      # Community mechanics resources
        workforce.py      # Workforce types and habitation
      tools/              # Thin MCP tool wrappers
        __init__.py
        materials.py
        buildings.py
        recipes.py
        planets.py
        exchange.py
        market_analysis.py
        cogm.py
        building_cost.py
        permit_io.py
        base_plans.py
        info.py
  cache/                  # JSON cache files (gitignored)
  docs/
    FIO/
      fio-swagger.json
    tools/                # Tool documentation
    design/               # Design documentation
```

**Architecture:** Tools are "ultra-thin" wrappers that validate input, delegate to `prun_lib`, and serialize output. Business logic in `prun_lib` is reusable as a standalone library.

## Tool Inventory

### Implemented Tools

#### Materials

| Tool | Description |
|------|-------------|
| `get_material_info` | Material details by ticker (supports comma-separated, e.g., "BSE,RAT,H2O") |
| `get_all_materials` | All materials from cache |
| `refresh_materials_cache` | Force refresh from FIO API |

#### Buildings

| Tool | Description |
|------|-------------|
| `get_building_info` | Building details by ticker (supports comma-separated) |
| `search_buildings` | Filter by expertise, workforce type, or construction materials |
| `refresh_buildings_cache` | Force refresh from FIO API |

#### Recipes

| Tool | Description |
|------|-------------|
| `get_recipe_info` | Recipes that produce a material (by output ticker) |
| `search_recipes` | Filter by building, input materials, or output materials |
| `refresh_recipes_cache` | Force refresh from FIO API |

#### Planets

| Tool | Description |
|------|-------------|
| `get_planet_info` | Planet details by name/ID (supports comma-separated) |
| `search_planets` | Find planets by resource criteria |

#### Exchange

| Tool | Description |
|------|-------------|
| `get_exchange_prices` | Full order book for material(s) at exchange(s) |
| `get_exchange_all` | Summary prices for all materials on exchange(s) |

#### Analysis Tools

| Tool | Description |
|------|-------------|
| `calculate_cogm` | Cost of Goods Manufactured for a recipe |
| `calculate_permit_io` | Daily material I/O for a base configuration |
| `calculate_building_cost` | Total material cost to build on a planet (incl. infrastructure) |

#### Market Analysis

| Tool | Description |
|------|-------------|
| `get_market_summary` | Quick market snapshot with actionable warnings (plain text) |
| `analyze_fill_cost` | Calculate expected cost/proceeds for a specific quantity |
| `get_order_book_depth` | Full order book in TOON tabular format |
| `get_price_history` | Historical price data in TOON tabular format |
| `get_price_history_summary` | Compare current market conditions to historical norms (plain text) |

#### Base Plans

| Tool | Description |
|------|-------------|
| `save_base_plan` | Create or update a base plan |
| `get_base_plan` | Retrieve a single base plan by name |
| `list_base_plans` | List all stored base plans (with optional active filter) |
| `delete_base_plan` | Remove a base plan |
| `calculate_plan_io` | Calculate daily I/O for a saved base plan |

#### Utility

| Tool | Description |
|------|-------------|
| `get_version` | Get prun-mcp server version |
| `get_cache_info` | Get cache status for all data caches |

---

### Future Work (Not Yet Implemented)

#### Trading Analysis Tools

| Tool | Description |
|------|-------------|
| `find_arbitrage` | Cross-exchange arbitrage opportunities |
| `compare_spreads` | Bid/ask spread comparison across exchanges |
| `calculate_production_profit` | COGM-based profit calculation with market prices |

#### Repair/Degradation Tools

| Tool | Description |
|------|-------------|
| `calculate_building_efficiency` | Efficiency at given days since repair |
| `calculate_repair_cost` | Material cost at given day count |
| `find_optimal_repair_interval` | Best repair timing based on profit vs repair cost |
| `get_repair_schedule` | Day-by-day efficiency and material tick data |

See [docs/mechanics/mechanics.md](docs/mechanics/mechanics.md) for game mechanics reference (building degradation, COGM calculations, etc.).



## External Resources

- [The Prosperous Universe Handbook Wiki](https://handbook.apex.prosperousuniverse.com/wiki/)
- [The Prosperous Universe Documentation GitHub repo](https://github.com/simulogics/prosperousuniverse-docs)
- [The Prodperous Universe Forums](https://com.prosperousuniverse.com/latest)
- [PrUn Community Derived Information](https://pct.fnar.net/)
- [Benten Economic Union Website](https://benten.space/)
- [MoonSugarTravels desgradation spreadsheet](https://docs.google.com/spreadsheets/d/1ELsfw4ii1hQFWDd-BL4JzwqHc-wGVXbJtvAeprv0pZ0)

## Design Decisions (Resolved)

- **Cache invalidation**: TTL-based (24h) with manual refresh tools (`refresh_*_cache`). Market data uses 2.5-minute in-memory cache.
- **Rate limiting**: Not needed - FIO is ok with no rate limiting ([source](https://fnar.net/page/projects/))
- **FIO API coverage**: Full coverage including materials, buildings, recipes, planets, exchange, market analysis, base planning
- **Tool grouping**: Entity-based organization (`materials.py`, `buildings.py`, etc.) rather than behavior-based
- **Error handling**: Return `[TextContent(...)]` for not-found cases; "not found" is not an error, just a result the LLM can reason about
- **Cache format**: JSON files (simpler than CSV, faster parsing, dict-based data)
- **Data models**: Pydantic models for FIO API responses (`models/fio.py`) and domain outputs (`models/domain.py`), providing type safety and validation
- **Architecture**: Ultra-thin tools pattern - MCP tools delegate to `prun_lib` for business logic, enabling library reuse without MCP dependency




