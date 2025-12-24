
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
| **Tool execution errors** | API failures, invalid data, business logic | Return result with `isError: true` |

**Pattern for FIO API failures:**

```python
@mcp.tool()
async def get_exchange_prices(ticker: str, exchange: str) -> str:
    try:
        data = await fio_client.get_exchange(ticker, exchange)
        return toon.encode(data)
    except FIONotFoundError:
        # Return error as tool result, not exception
        return ToolResult(
            content=[TextContent(text=f"Material '{ticker}' not found on exchange '{exchange}'")],
            isError=True
        )
    except FIOApiError as e:
        return ToolResult(
            content=[TextContent(text=f"FIO API error: {e}")],
            isError=True
        )
```

**Guidelines:**
- Use `isError=True` for expected failures (404, invalid ticker, no data)
- Let exceptions propagate for unexpected failures (network down, server crash)
- Include descriptive messages the LLM can reason about
- Never expose internal stack traces

### Caching Strategy

> **Note**: FIO recommends not caching their API responses as they've optimized with CloudFlare ([source](https://fnar.net/page/projects/)). However, selective caching is still useful for specific cases below.

- **Backend**: CSV files (human-inspectable, version-controllable)
- **Structure**: One file per "table" (materials.csv, buildings.csv, etc.)

**What to cache:**

| Data Type | Cache? | Reason | TTL |
|-----------|--------|--------|-----|
| Materials | Yes | Static, rarely changes | 24h or manual |
| Buildings | Yes | Static, rarely changes | 24h or manual |
| Recipes | Yes | Static, rarely changes | 24h or manual |
| Workforce needs | Yes | Static | 24h or manual |
| Exchange prices | No | Real-time data, FIO handles caching | - |
| Order books | No | Real-time data | - |
| Price history (CXPC) | Optional | For historical aggregation beyond FIO's intervals | On-demand |
| Planet data | Yes | Changes infrequently | 24h or manual |

**Invalidation**: TTL-based with manual refresh option via tool (e.g., `refresh_cache`)

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
      server.py           # FastMCP server initialization
      tools/              # Tool implementations
        __init__.py
        market.py         # Market/exchange tools
        production.py     # Recipe/production tools
        planets.py        # Planet/resource tools
        analysis.py       # Computed analysis tools
      fio/                # FIO API client
        __init__.py
        client.py         # HTTP client wrapper
        models.py         # Pydantic models for API responses
      cache/              # Caching layer
        __init__.py
        csv_store.py      # CSV-based cache implementation
      utils/              # Shared utilities
        __init__.py
        toon.py           # TOON encoding helpers
  cache/                  # CSV cache files (gitignored)
    materials.csv
    buildings.csv
    ...
  docs/
    FIO/
      fio-swagger.json
```

## Tool Inventory

### Market Tools

| Tool | Type | Description |
|------|------|-------------|
| `get_exchange_prices` | Raw | Current bid/ask for material at exchange |
| `get_order_book` | Raw | Full order book depth |
| `get_price_history` | Raw | Historical price data |
| `find_arbitrage` | Analysis | Cross-exchange arbitrage opportunities |
| `compare_spreads` | Analysis | Bid/ask spread comparison |

### Production Tools

| Tool | Type | Description |
|------|------|-------------|
| `get_recipe` | Raw | Production recipe for a material |
| `get_building_recipes` | Raw | All recipes for a building |
| `get_building_info` | Raw | Building details and requirements |
| `calculate_production_profit` | Analysis | Profit calculation with full cost accounting |

### Planet Tools

| Tool | Type | Description |
|------|------|-------------|
| `get_planet_info` | Raw | Planet details and resources |
| `search_planets` | Raw | Find planets by resource criteria |
| `calculate_building_cost` | Analysis | Total cost to build on a planet |

### Workforce Tools

| Tool | Type | Description |
|------|------|-------------|
| `calculate_workforce_consumption` | Analysis | Daily consumable needs |

### Repair/Degradation Tools

| Tool | Type | Description |
|------|------|-------------|
| `calculate_building_efficiency` | Analysis | Efficiency at given days since repair |
| `calculate_repair_cost` | Analysis | Material cost at given day count for a building + planet |
| `find_optimal_repair_interval` | Analysis | Best repair timing based on profit vs repair cost |
| `get_repair_schedule` | Raw | Day-by-day efficiency and material tick data |

#### Game Mechanics Reference

##### Budiling Degregation 

The following was borrowed from [MoonSugarTravels desgradation spreadsheet](https://docs.google.com/spreadsheets/d/1ELsfw4ii1hQFWDd-BL4JzwqHc-wGVXbJtvAeprv0pZ0)
**Efficiency Formula**

```
η = 0.33 + 0.67 / (1 + e^((1789/25000) × (D - 100.87)))
```

Where:
- η = condition/efficiency (range: 0.33 to 1.0)
- D = days since last repair
- 100.87 = inflection point (note: may be 107.87 due to a game bug)

Efficiency timeline:
- Days 0-30: ~100% (negligible loss)
- Day 60: noticeable drop begins
- Day 90: falls below 80%
- Day 180: approaches floor of 33%

**Repair Cost Formula**

```
RepairCost(material) = floor(BuildingCost(material) × D / 180)
```

- Applied independently to each construction material
- Includes environmental materials (SEA, INS, TSH, HSE, AEF, MGC) - these are required for every repair, not just initial construction
- At D=180, repair cost equals full building cost
- No difference between repair and demolish/rebuild

**Optimal Repair Interval**

Simple buildings (single dominant material):
```
OptimalInterval = 180 / BuildingCost(material)
```

Examples:
- EXT (16 BSE): ~11.25 days
- RIG (12 BSE): ~15 days  
- FRM (4 BBH + 4 BSE): ~45 days

Complex buildings require value-weighted analysis across all materials, optimizing for the point where daily profit minus amortized repair cost is maximized.

**Multi-Building Bases**

- Game tracks each building's condition individually
- Production line efficiency = average of all buildings of that type
- Orders take same time regardless of which building slot executes them


##### COGM (Cost of Goods Manufactured) Summary

The following was borrowed from [Benten / Katoa Welcome Guide](https://docs.google.com/document/u/0/d/10qdF6wEpZshm-ErQmjyELfjcDpuXh4ZJjlB_1Wcibk4)

COGM = total cost to produce one unit of a material. Components:

1. Workforce consumables - DW, RAT, OVE (and luxuries) for your workers
2. Input materials - ingredients consumed by the recipe (none for extractors)
3. Building degradation - amortized repair costs

**Calculation:**
```
COGM = (daily consumable cost + daily input cost + daily degradation cost) / units produced per day
```

**Example:** EXT producing GAL on Katoa

* 60 pioneers → 565.68 CIS/day consumables
* 116 CIS/day degradation
* 12.79 GAL/day output
* COGM = 53.29 CIS/unit

**Key insight:** Compare COGM to market price. If market < COGM, buy instead of produce.

**Ways to lower COGM:**

* Increase production speed (experts, luxury consumables like COF)
* Reduce input/consumable costs (self-produce or find cheaper sources)



## External Resources

- [The Prosperous Universe Handbook Wiki](https://handbook.apex.prosperousuniverse.com/wiki/)
- [The Prosperous Universe Documentation GitHub repo](https://github.com/simulogics/prosperousuniverse-docs)
- [PrUn Community Derived Information](https://pct.fnar.net/)
- [Benten Economic Union Website](https://benten.space/)
- [MoonSugarTravels desgradation spreadsheet](https://docs.google.com/spreadsheets/d/1ELsfw4ii1hQFWDd-BL4JzwqHc-wGVXbJtvAeprv0pZ0)

## Open Questions

- [x] Cache invalidation strategy: TTL-based, manual refresh commands, or both?
  - **Resolved**: TTL-based (24h for static data) with manual refresh tool
- [x] Rate limiting: Do we need to throttle requests?
  - **Resolved**: No - FIO is ok with no rate limiting ([source](https://fnar.net/page/projects/))
- [ ] FIO API coverage: Start with subset or comprehensive from the start?
- [ ] Tool grouping: By domain (market/production/planet) or by behavior (analysis/raw)?
- [x] Error handling patterns for FIO API failures
  - **Resolved**: Use MCP's `isError: true` for expected failures (404, invalid ticker); let exceptions propagate for unexpected failures




