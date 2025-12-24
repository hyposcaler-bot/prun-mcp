# Buildings Tools

Tools for accessing building data from the Prosperous Universe game.

## get_building_info

Get detailed information about one or more buildings by ticker symbol.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | Yes | Building ticker symbol(s). Single (e.g., "PP1") or comma-separated (e.g., "PP1,HB1,FRM") |

### Response

Returns TOON-encoded building data including:
- `BuildingId`: Unique identifier
- `Name`: Full building name
- `Ticker`: Short ticker symbol
- `Expertise`: Building expertise category (or null)
- `AreaCost`: Area required on a base
- `Pioneers`, `Settlers`, `Technicians`, `Engineers`, `Scientists`: Workforce requirements
- `BuildingCosts`: List of materials required for construction
- `Recipes`: List of production recipes available

### Examples

**Single building:**
```
get_building_info("PP1")
```

**Multiple buildings:**
```
get_building_info("PP1,HB1,FRM")
```

**Partial match (some not found):**
```
get_building_info("PP1,INVALID,HB1")
# Returns PP1 and HB1 data, plus not_found: ["INVALID"]
```

---

## search_buildings

Search for buildings by expertise, workforce type, or construction materials. Returns compact results (Ticker and Name only) - use `get_building_info` for full details.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `expertise` | string | No | Filter by expertise type |
| `workforce` | string | No | Filter by workforce type (buildings that require this workforce) |
| `commodity_tickers` | list[string] | No | Filter by construction materials (AND logic - must use ALL specified) |

**Valid expertise values:**
- AGRICULTURE
- CHEMISTRY
- CONSTRUCTION
- ELECTRONICS
- FOOD_INDUSTRIES
- FUEL_REFINING
- MANUFACTURING
- METALLURGY
- RESOURCE_EXTRACTION

**Valid workforce values:**
- Pioneers
- Settlers
- Technicians
- Engineers
- Scientists

### Response

Returns TOON-encoded list of matching buildings with Ticker and Name only.

### Examples

**All buildings (no filters):**
```
search_buildings()
```

**By expertise:**
```
search_buildings(expertise="MANUFACTURING")
```

**By workforce:**
```
search_buildings(workforce="Scientists")
```

**By construction materials:**
```
search_buildings(commodity_tickers=["BSE", "BBH"])
# Returns buildings that require BOTH BSE and BBH to construct
```

**Combined filters:**
```
search_buildings(expertise="MANUFACTURING", workforce="Scientists")
# Returns manufacturing buildings that require Scientists
```

---

## refresh_buildings_cache

Force refresh the buildings cache from the FIO API, bypassing the 24-hour TTL.

### Parameters

None.

### Response

Returns a status message with the number of buildings cached.

### Example

```
refresh_buildings_cache()
# "Cache refreshed with 84 buildings"
```
