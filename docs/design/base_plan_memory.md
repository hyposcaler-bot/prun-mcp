# Base Plan Storage Tools - Rough Design Spec

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
  "experts": {
    "agriculture": 0,
    "chemistry": 0,
    "construction": 0,
    "electronics": 0,
    "food_industries": 3,
    "fuel_refining": 0,
    "manufacturing": 0,
    "metallurgy": 0,
    "resource_extraction": 0
  },
  "infrastructure": [
    {"type": "HB1", "count": 5},
    {"type": "HB2", "count": 0},
    {"type": "HB3", "count": 0},
    {"type": "HB4", "count": 0},
    {"type": "HB5", "count": 0},
    {"type": "STO", "count": 0}
  ],
  "production": [
    {"building_type": "FP", "recipe": "RAT:FP", "count": 11},
    {"building_type": "FP", "recipe": "COF:FP", "count": 1}
  ],
  "notes": "Primary consumables production base",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Field Notes

| Field | Required | Notes |
|-------|----------|-------|
| name | Yes | Primary key, unique identifier |
| planet | Yes | Planet ID (e.g., "KW-020c") |
| planet_name | No | Human-readable name for convenience |
| cogc_program | No | Active COGC program if any |
| experts | No | Expert allocation, defaults to all zeros |
| infrastructure | Yes | Non-production buildings (HABs, STO) |
| production | Yes | Recipe assignments with counts |
| notes | No | Freeform text for human context |
| created_at | Auto | Set on creation |
| updated_at | Auto | Updated on save |

### Recipe Format

Recipes should use the standard prun format: `{OUTPUT}:{BUILDING}` or the full recipe ticker as used elsewhere in prun-mcp. Examples:
- `RAT:FP` — Rations from Food Processor
- `COF:FP` — Coffee from Food Processor
- `SF:REF` — Steel from Refinery

## Tool Interfaces

### save_base_plan

Creates or updates a base plan.

**Parameters:**
```
name: string (required) — Plan identifier
planet: string (required) — Planet ID
planet_name: string (optional) — Human-readable planet name
cogc_program: string (optional) — COGC program code
experts: object (optional) — Expert counts by category
infrastructure: array (required) — Infrastructure building configs (HABs, STO)
production: array (required) — Recipe assignments
notes: string (optional) — Freeform notes
```

**Behavior:**
- If plan with `name` exists, overwrites it (updates `updated_at`)
- If plan doesn't exist, creates it (sets both timestamps)
- Validates building types and recipe formats against known values
- Returns saved plan object

**Example call:**
```
save_base_plan(
  name="Starbucks Bastion",
  planet="KW-020c",
  planet_name="Milliways",
  cogc_program="FOOD",
  experts={"food_industries": 3},
  infrastructure=[{"type": "HB1", "count": 5}],
  production=[
    {"building_type": "FP", "recipe": "RAT:FP", "count": 11},
    {"building_type": "FP", "recipe": "COF:FP", "count": 1}
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
- Error/null if not found

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

## Storage Implementation

### File Structure

```
{data_dir}/
  base_plans/
    starbucks_bastion.json
    vertical_bootstrap.json
    ...
```

### Naming Convention

Filename derived from plan name:
- Lowercase
- Spaces → underscores
- Strip special characters
- Add `.json` extension

Example: `"Starbucks Bastion"` → `starbucks_bastion.json`

### Alternative: Single File

Could also use single file with all plans:
```
{data_dir}/base_plans.json
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

**Recommendation:** Start with single file for simplicity. Migrate to multi-file if plans get large or concurrent access becomes a concern.

## Integration with calculate_permit_io

### Current State

`calculate_permit_io` accepts recipe/count inputs directly. User must provide these manually each time.

### Future State

Two integration options:

**Option A: Wrapper Tool**

New tool `calculate_plan_io(plan_name)` that:
1. Calls `get_base_plan(plan_name)`
2. Extracts production recipes
3. Calls `calculate_permit_io` with extracted data
4. Returns enriched results (can include expert bonuses, COGC effects)

**Option B: Parameter Enhancement**

Modify `calculate_permit_io` to accept optional `plan_name` parameter:
- If provided, loads plan and uses its production config
- If not provided, works as today

**Recommendation:** Option A — keeps tools focused, easier to test, doesn't risk breaking existing tool.

## Validation Rules

### On Save

1. `name` must be non-empty string
2. `planet` must be valid planet ID (optional: validate against known planets)
3. `infrastructure[].type` must be valid infrastructure type (HB1-HB5, STO)
4. `infrastructure[].count` must be non-negative integer
5. `production[].building_type` must be valid building ticker
6. `production[].recipe` must be valid recipe format
7. `production[].count` must be positive integer
8. `experts` keys must be valid expert categories
9. `experts` values must be non-negative integers, likely max 5 each

### Strict vs Lenient

Start lenient — warn on unknown values but allow save. Can tighten later once patterns are established.

## Future Enhancements (Out of Scope for V1)

- Diff two plans
- Clone/copy plan
- Plan versioning / history
- Import from live base data
- Export to PrunPlanner format
- Workforce calculations from infrastructure
- Area calculations
- Cost projections

## Open Questions

1. Should experts be stored as object or array format?
2. Any other infrastructure building types beyond HB1-HB5 and STO to consider?