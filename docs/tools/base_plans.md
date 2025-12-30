# Base Plans Tools

Tools for storing and managing base plan configurations in Prosperous Universe. Plans persist across sessions and can be used to calculate I/O using current market prices.

## save_base_plan

Creates or updates a base plan with production recipes, habitation, and optional extraction operations.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Plan identifier (unique name) |
| `planet` | string | Yes | Planet ID (e.g., "KW-020c") |
| `habitation` | array | Yes | Habitation buildings. Each: `{"building": string, "count": int}` |
| `production` | array | Yes | Recipe assignments. Each: `{"recipe": string, "count": int, "efficiency": float}` |
| `planet_name` | string | No | Human-readable planet name |
| `cogc_program` | string | No | Active COGC program (e.g., "FOOD") |
| `expertise` | object | No | Expert counts by category (PascalCase keys) |
| `storage` | array | No | Storage buildings. Each: `{"building": string, "count": int, "capacity": int}` |
| `extraction` | array | No | Extraction operations. Each: `{"building": string, "resource": string, "count": int, "efficiency": float}` |
| `notes` | string | No | Freeform notes |
| `overwrite` | boolean | No | Must be true to update existing plan (default: false) |

### Expertise Keys

Valid expertise keys (PascalCase): `Agriculture`, `Chemistry`, `Construction`, `Electronics`, `FoodIndustries`, `FuelRefining`, `Manufacturing`, `Metallurgy`, `ResourceExtraction`

### Response

Returns TOON-encoded saved plan with timestamps and any validation warnings.

### Examples

**Basic RAT production base:**
```
save_base_plan(
  name="Milliways RAT",
  planet="KW-020c",
  habitation=[{"building": "HB1", "count": 5}],
  production=[
    {"recipe": "1xGRN 1xALG 1xVEG=>10xRAT", "count": 11, "efficiency": 1.38}
  ]
)
```

**With extraction and expertise:**
```
save_base_plan(
  name="Fuel Production",
  planet="UV-351a",
  planet_name="Fuel Hub",
  habitation=[{"building": "HB1", "count": 3}, {"building": "HB2", "count": 1}],
  extraction=[{"building": "EXT", "resource": "GAL", "count": 2, "efficiency": 1.03}],
  production=[
    {"recipe": "1xAMM 2xGAL 3xH=>100xSF", "count": 2, "efficiency": 1.2}
  ],
  expertise={"FuelRefining": 4, "ResourceExtraction": 1},
  notes="Vertically integrated SF production"
)
```

**Updating an existing plan:**
```
save_base_plan(
  name="Milliways RAT",
  planet="KW-020c",
  habitation=[{"building": "HB1", "count": 6}],
  production=[...],
  overwrite=true
)
```

---

## get_base_plan

Retrieves a single base plan by name.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Plan identifier |

### Response

Returns TOON-encoded plan data including all fields and timestamps, or error if not found.

### Examples

```
get_base_plan("Milliways RAT")
# Returns full plan data
```

---

## list_base_plans

Lists all stored base plans with summary information.

### Parameters

None.

### Response

Returns TOON-encoded array of plan summaries:
- `name`: Plan identifier
- `planet`: Planet ID
- `planet_name`: Human-readable name (if set)
- `updated_at`: Last update timestamp

### Examples

```
list_base_plans()
# Returns summaries of all saved plans
```

---

## delete_base_plan

Removes a base plan from storage.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Plan identifier |

### Response

Returns success confirmation or error if not found.

### Examples

```
delete_base_plan("Old Expansion Plan")
# Returns {"deleted": "Old Expansion Plan", "success": true}
```

---

## calculate_plan_io

Calculates daily material I/O for a saved base plan using current market prices.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Plan identifier |
| `exchange` | string | Yes | Exchange code for pricing. Valid: AI1, CI1, CI2, IC1, NC1, NC2. |

### Response

Returns TOON-encoded I/O breakdown (same format as `calculate_permit_io`):
- `exchange`: Exchange used for pricing
- `materials`: List of material flows (ticker, in, out, delta, cis_per_day)
- `workforce`: Required workers by type
- `habitation`: Capacity validation (required vs available)
- `area`: Area usage validation (used vs limit)
- `totals`: Net CIS/day profit

### Examples

```
calculate_plan_io("Milliways RAT", "CI1")
# Returns full I/O analysis with current CI1 prices
```

---

## Workflow

1. **Find recipes** using `get_recipe_info` or `search_recipes`:
   ```
   get_recipe_info("RAT")
   # Returns all recipes that produce RAT with their RecipeName values
   ```

2. **Check planet resources** (if using extraction):
   ```
   get_planet_info("UV-351a")
   # Returns planet resources with extraction factors
   ```

3. **Create the plan**:
   ```
   save_base_plan(
     name="My Base",
     planet="UV-351a",
     habitation=[...],
     production=[...],
     extraction=[...]
   )
   ```

4. **Calculate I/O** to analyze profitability:
   ```
   calculate_plan_io("My Base", "CI1")
   ```

5. **Iterate**: Update the plan with `overwrite=true` and recalculate.

---

## Notes

- Plans persist in `{PRUN_MCP_CACHE_DIR}/base_plans.json` (human-readable JSON)
- Validation is lenient: unknown values produce warnings but plans still save
- `calculate_plan_io` calls `calculate_permit_io` internally with plan data
- Extraction output is auto-calculated from planet resource factors using the PCT formula
- Exchange prices are fetched fresh on each `calculate_plan_io` call
- See `exchange://list` resource for exchange code-to-name mapping
