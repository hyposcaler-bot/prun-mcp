# Planets Tools

Tools for accessing planet data from the Prosperous Universe game.

## get_planet_info

Get information about one or more planets by identifier.

**Note:** Planet data is fetched directly from the FIO API each time (no caching) because planet information includes dynamic data that changes frequently.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `planet` | string | Yes | Planet identifier(s). Single (e.g., "Katoa") or comma-separated (e.g., "Katoa,Montem,Promitor"). Accepts PlanetId, PlanetNaturalId (e.g., "XK-745b"), or PlanetName. |

### Response

Returns TOON-encoded planet data including:
- `PlanetId`: Unique identifier
- `PlanetNaturalId`: Natural ID (e.g., "XK-745b")
- `PlanetName`: Planet name
- `Gravity`, `Pressure`, `Temperature`, `Radiation`: Environmental factors
- `Fertility`, `Sunlight`: Agricultural factors
- `Surface`: Whether the planet has a surface
- `FactionCode`, `FactionName`: Faction information
- `Resources`: List of available resources with extraction factors
- `BuildRequirements`: Materials needed for base construction
- `HasLocalMarket`, `HasWarehouse`, `HasShipyard`: Infrastructure availability
- And many more properties

### Examples

**Single planet by name:**
```
get_planet_info("Katoa")
```

**Single planet by natural ID:**
```
get_planet_info("XK-745b")
```

**Multiple planets:**
```
get_planet_info("Katoa,Montem,Promitor")
```

**Partial match (some not found):**
```
get_planet_info("Katoa,INVALID,Montem")
# Returns Katoa and Montem data, plus not_found: ["INVALID"]
```

---

## search_planets

Search for planets by resource criteria.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `include_resources` | string | No | None | Comma-separated material tickers that must be present (e.g., "FEO,LST"). Maximum 4 materials. API returns planets containing ALL specified materials. |
| `exclude_resources` | string | No | None | Comma-separated material tickers to exclude (e.g., "H2O,O"). Client-side filtering. |
| `limit` | int | No | 20 | Maximum planets to return. |
| `top_resources` | int | No | 3 | Number of top resources to show per planet, sorted by extraction factor. |

### Response

Returns TOON-encoded list of planets:

```toon
[
  {
    name: "Promitor"
    id: "AB-123a"
    gravity: 0.92
    temperature: 22.5
    fertility: 0.95
    resources: "FEO:0.35,LST:0.28,H2O:0.12"
  }
  ...
]
```

Fields:
- `name`: Planet name
- `id`: Planet natural ID
- `gravity`: Gravity factor
- `temperature`: Surface temperature
- `fertility`: Fertility rating (-1 if not applicable)
- `resources`: Top resources by factor, format "TICKER:factor,..."

### Examples

**Find planets with iron ore:**
```
search_planets(include_resources="FEO")
```

**Find planets with both iron and limestone:**
```
search_planets(include_resources="FEO,LST")
```

**Find planets with iron but not water:**
```
search_planets(include_resources="FEO", exclude_resources="H2O")
```

**Get top 5 planets with more resources shown:**
```
search_planets(include_resources="FEO", limit=5, top_resources=5)
```

### Notes

- The FIO API supports up to 4 materials in `include_resources`
- `exclude_resources` is filtered client-side (API doesn't support exclusion)
- Resources are sorted by extraction factor (highest first)
- Planets without any resources are excluded from results
