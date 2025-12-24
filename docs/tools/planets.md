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
