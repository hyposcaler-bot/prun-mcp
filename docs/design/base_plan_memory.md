# Base Plan Storage Tools - Design Spec

## Overview

Add persistent storage for base plan configurations to prun-mcp server. Allows storing, retrieving, and managing base plans that can be used as inputs to existing calculation tools like `calculate_permit_io`.

## Data Model

### Base Plan Schema

```json
{
  "name": "Starbucks Bastion",
  "planet": "KW-020c",
  "planet_name": "Milliways",
  "cogc_program": "FOOD",
  "expertise": {
    "Agriculture": 0,
    "Chemistry": 0,
    "Construction": 0,
    "Electronics": 0,
    "FoodIndustries": 3,
    "FuelRefining": 0,
    "Manufacturing": 0,
    "Metallurgy": 0,
    "ResourceExtraction": 0
  },
  "habitation": [
    {"building": "HB1", "count": 5},
    {"building": "HB2", "count": 0}
  ],
  "storage": [
    {"building": "STO", "count": 2, "capacity": 1000}
  ],
  "extraction": [
    {"building": "EXT", "resource": "GAL", "count": 2, "efficiency": 1.03}
  ],
  "production": [
    {
      "recipe": "1xGRN 1xALG 1xVEG=>10xRAT",
      "count": 11,
      "efficiency": 1.33
    },
    {
      "recipe": "1xH2O 4xCOF=>4xKOM",
      "count": 1,
      "efficiency": 1.33
    }
  ],
  "notes": "Primary consumables production base",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Field Notes

| Field | Required | Notes |
|-------|----------|-------|
| name | Yes | Unique identifier (LLM-facing); implementation may use UUID internally |
| planet | Yes | Planet ID (e.g., "KW-020c") |
| planet_name | No | Human-readable name for convenience |
| cogc_program | No | Active COGC program if any |
| expertise | No | Expert allocation using game conventions, defaults to all zeros |
| habitation | Yes | Habitation buildings (HB1-HB5) with counts |
| storage | No | Storage buildings with capacity tracking |
| extraction | No | Resource extraction operations (EXT, RIG, COL) |
| production | Yes | Recipe assignments with counts and efficiency |
| notes | No | Freeform text for human context |
| created_at | Auto | Set on creation |
| updated_at | Auto | Updated on save |

### Recipe Format

Recipes use full recipe names as returned by the FIO API and used by `calculate_permit_io`. Examples:
- `1xGRN 1xALG 1xVEG=>10xRAT` — Rations from Food Processor
- `1xH2O 4xCOF=>4xKOM` — Kombucha from Food Processor
- `6xFE=>3xST` — Steel from Smelter

Use `get_recipe_info` or `search_recipes` to find valid recipe names.

### Expertise Format

Use game conventions (PascalCase):
- `Agriculture`
- `Chemistry`
- `Construction`
- `Electronics`
- `FoodIndustries`
- `FuelRefining`
- `Manufacturing`
- `Metallurgy`
- `ResourceExtraction`

### Efficiency

Efficiency is stored per-production-entry as a multiplier (e.g., `1.33` = 133%).

> **Note:** Future versions may calculate efficiency from expertise + COGC program. This will be a breaking change once the efficiency formula is implemented.

### Extraction Format

Resource extraction operations for EXT, RIG, and COL buildings:

```json
"extraction": [
  {"building": "EXT", "resource": "GAL", "count": 2, "efficiency": 1.03}
]
```

| Field | Required | Description |
|-------|----------|-------------|
| building | Yes | Extraction building: EXT (minerals), RIG (gas), COL (liquids) |
| resource | Yes | Material ticker to extract (e.g., "GAL", "FEO", "H2O") |
| count | Yes | Number of extraction buildings |
| efficiency | No | Efficiency multiplier (default: 1.0) |

Output is auto-calculated using the PCT formula:
```
daily_output = (resource_factor × 100) × base_multiplier × efficiency × count
```

| Building | Resource Type | Base Multiplier | Pioneers | Area |
|----------|---------------|-----------------|----------|------|
| EXT | Mineral | 0.7 | 60 | 25 |
| RIG | Gas/Atmospheric | 0.7 | 30 | 10 |
| COL | Liquid | 0.6 | 50 | 15 |

## Tool Interfaces

### save_base_plan

Creates or updates a base plan.

**Parameters:**
```
name: string (required) — Plan identifier
planet: string (required) — Planet ID
planet_name: string (optional) — Human-readable planet name
cogc_program: string (optional) — COGC program code
expertise: object (optional) — Expert counts by category (PascalCase keys)
habitation: array (required) — Habitation building configs
storage: array (optional) — Storage building configs with capacity
extraction: array (optional) — Resource extraction operations (EXT, RIG, COL)
production: array (required) — Recipe assignments with efficiency
notes: string (optional) — Freeform notes
overwrite: boolean (optional) — Must be true to update existing plan
```

**Behavior:**
- If plan with `name` exists and `overwrite` is not `true`, returns error
- If plan with `name` exists and `overwrite` is `true`, updates it (updates `updated_at`)
- If plan doesn't exist, creates it (sets both timestamps)
- Validates building types and recipe formats against known values (lenient: warns but allows)
- Returns saved plan object

**Example call:**
```
save_base_plan(
  name="Starbucks Bastion",
  planet="KW-020c",
  planet_name="Milliways",
  cogc_program="FOOD",
  expertise={"FoodIndustries": 3},
  habitation=[{"building": "HB1", "count": 5}],
  storage=[{"building": "STO", "count": 2, "capacity": 1000}],
  extraction=[{"building": "EXT", "resource": "GAL", "count": 2, "efficiency": 1.03}],
  production=[
    {"recipe": "1xGRN 1xALG 1xVEG=>10xRAT", "count": 11, "efficiency": 1.33},
    {"recipe": "1xH2O 4xCOF=>4xKOM", "count": 1, "efficiency": 1.33}
  ],
  notes="Primary consumables production"
)
```

### get_base_plan

Retrieves a single base plan by name.

**Parameters:**
```
name: string (required) — Plan identifier
```

**Returns:**
- Full plan object if found
- Error message if not found

**Example call:**
```
get_base_plan(name="Starbucks Bastion")
```

### list_base_plans

Lists all stored base plans.

**Parameters:**
```
None (or optional filters later)
```

**Returns:**
- Array of plan summaries: `[{name, planet, planet_name, updated_at}, ...]`
- Empty array if no plans stored

**Example call:**
```
list_base_plans()
```

### delete_base_plan

Removes a base plan.

**Parameters:**
```
name: string (required) — Plan identifier
```

**Returns:**
- Success confirmation
- Error if not found

**Example call:**
```
delete_base_plan(name="Old Expansion Plan")
```

### calculate_plan_io

Calculates daily I/O for a saved base plan.

**Parameters:**
```
name: string (required) — Plan identifier
exchange: string (required) — Exchange code for pricing (e.g., "CI1")
```

**Behavior:**
1. Loads plan via `get_base_plan(name)`
2. Transforms plan data to `calculate_permit_io` format
3. Calls `calculate_permit_io` with extracted data
4. Returns enriched results

**Example call:**
```
calculate_plan_io(name="Starbucks Bastion", exchange="CI1")
```

## Storage Implementation

### Data Directory

Uses the same directory as the cache, configured via `PRUN_MCP_CACHE_DIR` environment variable (default: `cache/`).

### File Structure

Single file containing all plans:
```
{cache_dir}/base_plans.json
```

Containing:
```json
{
  "plans": {
    "Starbucks Bastion": { ... },
    "Vertical Bootstrap": { ... }
  }
}
```

### File Format

Human-readable JSON with indentation (2 spaces).

### Concurrent Access

Use atomic writes to prevent corruption:

```python
def save_plans(plans: dict, path: Path) -> None:
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(plans, f, indent=2)
    temp_path.rename(path)  # Atomic on POSIX
```

This is sufficient for typical MCP usage where tool calls are sequential within a session. If concurrent access becomes a concern, consider file locking or migration to SQLite.

## Integration with calculate_permit_io

### Approach

Use a wrapper tool (`calculate_plan_io`) rather than modifying `calculate_permit_io`. This:
- Keeps tools focused and single-purpose
- Easier to test independently
- Doesn't risk breaking existing tool behavior

### Data Transformation

`calculate_plan_io` transforms stored plan format to `calculate_permit_io` input:

| Plan Field | Permit I/O Field |
|------------|------------------|
| `production[].recipe` | `production[].recipe` |
| `production[].count` | `production[].count` |
| `production[].efficiency` | `production[].efficiency` |
| `habitation[].building` | `habitation[].building` |
| `habitation[].count` | `habitation[].count` |
| `extraction[].building` | `extraction[].building` |
| `extraction[].resource` | `extraction[].resource` |
| `extraction[].count` | `extraction[].count` |
| `extraction[].efficiency` | `extraction[].efficiency` |
| `planet` | `planet` (required if extraction present) |

## Validation Rules

### On Save

1. `name` must be non-empty string
2. `planet` must be non-empty string
3. `habitation[].building` must be valid habitation type (HB1-HB5)
4. `habitation[].count` must be non-negative integer
5. `storage[].building` must be valid storage type (STO)
6. `storage[].count` must be non-negative integer
7. `storage[].capacity` must be positive integer
8. `extraction[].building` must be valid extraction type (EXT, RIG, COL)
9. `extraction[].resource` must be non-empty string
10. `extraction[].count` must be positive integer
11. `extraction[].efficiency` must be positive number (if provided)
12. `production[].recipe` should be valid recipe format (warn if unknown)
13. `production[].count` must be positive integer
14. `production[].efficiency` must be positive number
15. `expertise` keys must be valid expertise categories (PascalCase)
16. `expertise` values must be non-negative integers (max 5 each)

### Validation Mode

Start lenient — warn on unknown values but allow save. Can tighten later once patterns are established.

## Multi-Plan Operations

Base plans are independent entities. They do not reference each other.