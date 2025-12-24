# Materials Tools

Tools for accessing material data from the Prosperous Universe game.

## get_material_info

Get information about one or more materials by ticker symbol or MaterialId.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | Yes | Material ticker symbol(s) or MaterialId(s). Single (e.g., "BSE") or comma-separated (e.g., "BSE,RAT,H2O"). Also accepts 32-character hex MaterialId. |

### Response

Returns TOON-encoded material data including:
- `MaterialId`: Unique identifier
- `Name`: Full material name
- `Ticker`: Short ticker symbol
- `CategoryName`: Material category
- `Weight`: Weight per unit
- `Volume`: Volume per unit

### Examples

**Single material:**
```
get_material_info("BSE")
```

**Multiple materials:**
```
get_material_info("BSE,RAT,H2O")
```

**Partial match (some not found):**
```
get_material_info("BSE,INVALID,H2O")
# Returns BSE and H2O data, plus not_found: ["INVALID"]
```

**By MaterialId (useful for cross-referencing from planet data):**
```
get_material_info("ec8dbb1d3f51d89c61b6f58fdd64a7f0")
```

---

## refresh_materials_cache

Force refresh the materials cache from the FIO API, bypassing the 24-hour TTL.

### Parameters

None.

### Response

Returns a status message with the number of materials cached.

### Example

```
refresh_materials_cache()
# "Cache refreshed with 287 materials"
```

---

## get_all_materials

Get all materials from the cache.

### Parameters

None.

### Response

Returns TOON-encoded list of all materials with their properties.

> **Note:** This returns a large dataset. Consider using `get_material_info` with specific tickers when possible.
