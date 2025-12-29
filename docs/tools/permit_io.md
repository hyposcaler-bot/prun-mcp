# Permit I/O Tools

Tools for calculating daily material inputs and outputs for a base permit in Prosperous Universe.

## calculate_permit_io

Calculate the daily material flow for a base, showing inputs, outputs, deltas, and CIS/day value.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `production` | array | Yes | List of production lines. Each entry: `{"recipe": string, "count": int, "efficiency": float}` |
| `habitation` | array | Yes | List of habitation buildings. Each entry: `{"building": string, "count": int}` |
| `exchange` | string | Yes | Exchange code for pricing (e.g., "CI1"). Valid: AI1, CI1, CI2, IC1, NC1, NC2. |
| `permits` | integer | No | Number of permits for this base (default: 1). Area limits: 1=500, 2=750, 3=1000. |
| `extraction` | array | No | List of extraction operations. Each entry: `{"building": string, "resource": string, "count": int, "efficiency": float}` |
| `planet` | string | No | Planet identifier (required if `extraction` is provided). Used to look up resource factors. |

### Production Entry

| Field | Type | Description |
|-------|------|-------------|
| `recipe` | string | Recipe name (e.g., "1xGRN 1xALG 1xVEG=>10xRAT") |
| `count` | integer | Number of buildings running this recipe |
| `efficiency` | float | Efficiency multiplier (e.g., 1.406 for 140.6%) |

### Habitation Entry

| Field | Type | Description |
|-------|------|-------------|
| `building` | string | Habitation building ticker (HB1-HB5, HBB, HBC, HBM, HBL) |
| `count` | integer | Number of buildings |

### Extraction Entry

| Field | Type | Description |
|-------|------|-------------|
| `building` | string | Extraction building ticker: EXT (minerals), RIG (gas), COL (liquids) |
| `resource` | string | Material ticker to extract (e.g., "GAL", "FEO", "H2O") |
| `count` | integer | Number of extraction buildings |
| `efficiency` | float | Efficiency multiplier (e.g., 1.03 for 103%). Default: 1.0 |

**Extraction Formula (PCT):**
```
daily_output = (resource_factor × 100) × base_multiplier × efficiency × count
```

| Building | Resource Type | Base Multiplier | Pioneers | Area |
|----------|---------------|-----------------|----------|------|
| EXT | Mineral | 0.7 | 60 | 25 |
| RIG | Gas/Atmospheric | 0.7 | 30 | 10 |
| COL | Liquid | 0.6 | 50 | 15 |

### Response

Returns TOON-encoded daily I/O breakdown including:

- `exchange`: Exchange used for pricing
- `materials`: List of material flows
  - `ticker`: Material ticker
  - `in`: Daily input required (recipe inputs + workforce consumables)
  - `out`: Daily output produced
  - `delta`: Out - In (positive = surplus, negative = deficit)
  - `cis_per_day`: Value of delta (surplus sold at Bid, deficit bought at Ask)
- `workforce`: Required workers by type
- `habitation`: Capacity validation
  - `validation`: Per-type capacity check (required vs available)
  - `sufficient`: Boolean indicating if housing is adequate
- `area`: Area usage validation
  - `used`: Total area consumed by buildings
  - `limit`: Area limit based on permits (500/750/1000)
  - `permits`: Number of permits
  - `remaining`: Limit - used (can be negative)
  - `sufficient`: Boolean indicating if within area limit
- `totals`: Summary
  - `cis_per_day`: Net daily profit/loss
- `errors`: List of any errors (missing recipes, etc.)
- `missing_prices`: List of materials with no market price

### Examples

**Basic permit I/O:**
```json
calculate_permit_io(
  production=[{"recipe": "1xGRN 1xALG 1xVEG=>10xRAT", "count": 12, "efficiency": 1.406}],
  habitation=[{"building": "HB1", "count": 5}],
  exchange="CI1"
)
```

**Multiple production lines:**
```json
calculate_permit_io(
  production=[
    {"recipe": "1xGRN 1xALG 1xVEG=>10xRAT", "count": 10, "efficiency": 1.4},
    {"recipe": "1xCAF 3xDW=>3xCOF", "count": 2, "efficiency": 1.4}
  ],
  habitation=[{"building": "HB1", "count": 5}],
  exchange="CI1"
)
```

**Mixed workforce with multiple habitation types:**
```json
calculate_permit_io(
  production=[
    {"recipe": "some-pioneer-recipe", "count": 5, "efficiency": 1.2},
    {"recipe": "some-settler-recipe", "count": 3, "efficiency": 1.2}
  ],
  habitation=[
    {"building": "HBB", "count": 4}  # 75 Pioneers + 75 Settlers each
  ],
  exchange="NC1"
)
```

**Expanded base with 2 permits (750 area limit):**
```json
calculate_permit_io(
  production=[{"recipe": "1xGRN 1xALG 1xVEG=>10xRAT", "count": 40, "efficiency": 1.4}],
  habitation=[{"building": "HB1", "count": 8}],
  exchange="CI1",
  permits=2
)
```

**With resource extraction:**
```json
calculate_permit_io(
  production=[
    {"recipe": "1xAMM 2xGAL 3xH=>100xSF", "count": 2, "efficiency": 1.2}
  ],
  habitation=[{"building": "HB1", "count": 3}],
  extraction=[
    {"building": "EXT", "resource": "GAL", "count": 1, "efficiency": 1.03}
  ],
  planet="UV-351a",
  exchange="CI1"
)
```

---

## Workflow

1. **Find recipes** using `get_recipe_info` or `search_recipes`:
   ```
   get_recipe_info("RAT")
   # Returns all recipes that produce RAT
   ```

2. **Check habitation capacities** using the resource:
   ```
   Read resource: workforce://habitation
   # Shows capacity per building type
   ```

3. **Calculate permit I/O**:
   ```
   calculate_permit_io(production=[...], habitation=[...], exchange="CI1")
   ```

4. **Analyze results**:
   - Positive `delta` = selling surplus at Bid price
   - Negative `delta` = buying deficit at Ask price
   - Check `habitation.sufficient` for housing validation
   - Check `area.sufficient` for area limit validation

---

## Notes

- Workforce consumable rates are fetched from FIO API and cached (24h TTL)
- Recipe and building data are cached (24h TTL)
- Exchange prices are fetched fresh on each call
- Delta calculation: `out - in` (positive = surplus to sell)
- Pricing: Surplus sold at Bid, deficit bought at Ask (immediate market prices)
- See `workforce://habitation` resource for valid habitation buildings and capacities
