# MCP Resources Design

## Current State

Resources provide static reference data and documentation via MCP resource URIs. Unlike tools, resources don't fetch live data - they return pre-defined content.

## Resource Inventory

| File | URIs | Purpose |
|------|------|---------|
| `exchanges.py` | `exchange://list` | Exchange codes and names |
| `workforce.py` | `workforce://types`, `workforce://habitation` | Worker types, habitation capacity |
| `buildings.py` | `buildings://efficiency/*` (5 URIs) | Efficiency mechanics documentation |
| `mechanics.py` | `pct-mechanics://*` (8 URIs) | Community-derived game formulas |
| `extraction.py` | *(none - utility only)* | Constants for EXT/RIG/COL calculations |

## Detailed Breakdown

### exchanges.py
- **`exchange://list`**: Human-readable table of exchange codes (AI1, CI1, etc.)
- Exports: `EXCHANGES`, `VALID_EXCHANGES`, `format_exchange_list()`

### workforce.py
- **`workforce://types`**: Ordered list (Pioneers → Scientists)
- **`workforce://habitation`**: Table of HB1-HB5, HBB/HBC/HBM/HBL capacities
- Exports: `WORKFORCE_TYPES`, `HABITATION_CAPACITY`, `VALID_HABITATION`

### buildings.py
- **`buildings://efficiency`**: Overview of efficiency formula
- **`buildings://efficiency/workforce`**: Workforce satisfaction impact
- **`buildings://efficiency/experts`**: Expert bonus system (~6% to ~28.4%)
- **`buildings://efficiency/cogc`**: CoGC ADVERTISING programs (up to 25%)
- **`buildings://efficiency/condition`**: Building degradation impact
- No exports (pure documentation)

### mechanics.py
- **`pct-mechanics://list`**: Index of available topics
- **`pct-mechanics://{topic}`**: Reads markdown from `data/community-mechanics/content/{topic}/_index.md`
- Topics: arc, building-degradation, hq, planet, population-infrastructure, ship-blueprints, workforce

### extraction.py
- **Not an MCP resource** - utility module for extraction calculations
- Exports: `EXTRACTION_BUILDINGS`, `RESOURCE_TYPE_TO_BUILDING`, `VALID_EXTRACTION_BUILDINGS`, `calculate_extraction_output()`, `get_building_for_resource_type()`
- Used by: `permit_io.py`, `base_plans.py`
- got stuphed under /resources, cause some how it made sense and still working out patterns for resources

---

## Issues / Areas in Flux

### 1. Inconsistent Export Patterns
- `__init__.py` only exports from `extraction.py`
- Other modules are imported directly where needed
- Should all canonical data (WORKFORCE_TYPES, EXCHANGES, etc.) be centralized?

### 2. Overlapping Documentation
- `buildings.py` has hand-written efficiency docs
- `mechanics.py` serves community mechanics markdown
- Both cover building degradation, workforce formulas
- Which is authoritative? Should buildings.py defer to pct-mechanics?

### 3. extraction.py Placement
- Contains constants + calculation logic, not MCP resources
- Should it be in `resources/` or a separate `utils/` or `constants/` module?
- Currently exported from `resources/__init__.py` which is confusing

### 4. Data Duplication
- Workforce types defined in `workforce.py`
- Also used from FIO API via `WorkforceCache`
- Habitation buildings hardcoded vs. could be derived from FIO buildings data

### 5. Missing Resources
Potential additions:
- `extraction://buildings` - EXT/RIG/COL specs as MCP resource
- `buildings://list` - All building tickers with basic info
- `materials://categories` - Material categories

### 6. URI Scheme Consistency
Current schemes:
- `exchange://` (singular)
- `workforce://`
- `buildings://`
- `pct-mechanics://`

No clear convention. Consider standardizing (e.g., all plural or all singular).

---

## Recommendations

1. **Move extraction.py** to a new `utils/` or `constants/` package
2. **Centralize canonical data exports** in `resources/__init__.py`
3. **Deprecate overlapping docs** in `buildings.py` in favor of `pct-mechanics://`
4. **Add extraction resource** to expose EXT/RIG/COL as MCP resource
5. **Document URI scheme convention** and apply consistently

---

## Implementation Notes

### Adding a New Resource

```python
from prun_mcp.app import mcp

@mcp.resource("scheme://path")
def resource_name() -> str:
    """Docstring becomes resource description."""
    return "content"
```

### Registering in server.py

Resources are auto-registered when their module is imported:
```python
from prun_mcp.resources import new_module  # noqa: F401
```

### Testing

Resources don't need async tests (no I/O). Test the format functions and ensure files exist for mechanics.
