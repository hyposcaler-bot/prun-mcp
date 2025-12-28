
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
| Exchange prices | No | Real-time data, rely on upstream doing the right thing for them | - |
| Order books | No | Real-time data | - |
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
      cache/              # JSON-based caching layer
        __init__.py
        materials_cache.py  # 24h TTL
        buildings_cache.py  # 24h TTL
        recipes_cache.py    # 24h TTL
      tools/              # Entity-based tool organization
        __init__.py
        materials.py      # get_material_info, get_all_materials, refresh
        buildings.py      # get_building_info, search_buildings, refresh
        recipes.py        # get_recipe_info, search_recipes, refresh
        planets.py        # get_planet_info
        exchange.py       # get_exchange_prices, get_exchange_all
  cache/                  # JSON cache files (gitignored)
    materials.json
    buildings.json
    recipes.json
  docs/
    FIO/
      fio-swagger.json
    tools/                # Tool documentation
      materials.md
      buildings.md
      recipes.md
      planets.md
      exchange.md
```

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

#### Exchange

| Tool | Description |
|------|-------------|
| `get_exchange_prices` | Full order book for material(s) at exchange(s) |
| `get_exchange_all` | Summary prices for all materials on exchange(s) |

---

### Future Work (Not Yet Implemented)

#### Raw Data Tools

| Tool | Description |
|------|-------------|
| `get_price_history` | Historical CXPC price data |
| `search_planets` | Find planets by resource criteria |

#### Analysis Tools

These tools require server-side computation and return plain text summaries:

| Tool | Description |
|------|-------------|
| `find_arbitrage` | Cross-exchange arbitrage opportunities |
| `compare_spreads` | Bid/ask spread comparison |
| `calculate_production_profit` | COGM-based profit calculation |
| `calculate_building_cost` | Total cost to build on a planet |
| `calculate_workforce_consumption` | Daily consumable needs |

#### Repair/Degradation Tools

| Tool | Description |
|------|-------------|
| `calculate_building_efficiency` | Efficiency at given days since repair |
| `calculate_repair_cost` | Material cost at given day count |
| `find_optimal_repair_interval` | Best repair timing based on profit vs repair cost |
| `get_repair_schedule` | Day-by-day efficiency and material tick data |

See [docs/mechanics.md](docs/mechanics.md) for game mechanics reference (building degradation, COGM calculations, etc.).



## External Resources

- [The Prosperous Universe Handbook Wiki](https://handbook.apex.prosperousuniverse.com/wiki/)
- [The Prosperous Universe Documentation GitHub repo](https://github.com/simulogics/prosperousuniverse-docs)
- [The Prodperous Universe Forums](https://com.prosperousuniverse.com/latest)
- [PrUn Community Derived Information](https://pct.fnar.net/)
- [Benten Economic Union Website](https://benten.space/)
- [MoonSugarTravels desgradation spreadsheet](https://docs.google.com/spreadsheets/d/1ELsfw4ii1hQFWDd-BL4JzwqHc-wGVXbJtvAeprv0pZ0)

## Design Decisions (Resolved)

- **Cache invalidation**: TTL-based (24h) with manual refresh tools (`refresh_*_cache`)
- **Rate limiting**: Not needed - FIO is ok with no rate limiting ([source](https://fnar.net/page/projects/))
- **FIO API coverage**: Started with core subset (materials, buildings, recipes, planets, exchange); analysis tools deferred
- **Tool grouping**: Entity-based organization (`materials.py`, `buildings.py`, etc.) rather than behavior-based
- **Error handling**: Return `[TextContent(...)]` for not-found cases; "not found" is not an error, just a result the LLM can reason about
- **Cache format**: JSON files (simpler than CSV, faster parsing, dict-based data)
- **Data models**: Dict-based (no Pydantic) - TOON handles serialization directly




