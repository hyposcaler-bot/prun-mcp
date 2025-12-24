# FIO REST API Reference

Base URL: `https://rest.fnar.net`
Documentation: `https://doc.fnar.net`
Swagger Spec: `fio-swagger.json` (local copy)

## Exchange Price Chart Data (CXPC)

### Endpoints

```
GET /exchange/cxpc/{Ticker}.{Exchange}
GET /exchange/cxpc/{Ticker}.{Exchange}/{TimestampMs}
```

The optional `TimestampMs` parameter filters to return data since that epoch timestamp (milliseconds).

### Available Intervals

| Interval          | Granularity  | Notes                     |
|-------------------|--------------|---------------------------|
| `MINUTE_FIVE`     | 5 minutes    | Most granular available   |
| `MINUTE_FIFTEEN`  | 15 minutes   |                           |
| `MINUTE_THIRTY`   | 30 minutes   |                           |
| `HOUR_ONE`        | 1 hour       |                           |
| `HOUR_TWO`        | 2 hours      |                           |
| `HOUR_FOUR`       | 4 hours      |                           |
| `HOUR_SIX`        | 6 hours      |                           |
| `HOUR_TWELVE`     | 12 hours     |                           |
| `DAY_ONE`         | 1 day        | Currently used by server  |
| `DAY_THREE`       | 3 days       | Least granular            |

### Response Schema

```json
[
  {
    "Interval": "MINUTE_FIVE",
    "DateEpochMs": 1766430300000,
    "Open": 175.0,
    "Close": 175.0,
    "High": 175.0,
    "Low": 175.0,
    "Volume": 14000.0,
    "Traded": 80
  }
]
```

| Field        | Type    | Description                              |
|--------------|---------|------------------------------------------|
| `Interval`   | string  | Time interval identifier                 |
| `DateEpochMs`| int64   | Candle start timestamp (ms since epoch)  |
| `Open`       | float64 | Opening price for the interval           |
| `Close`      | float64 | Closing price for the interval           |
| `High`       | float64 | Highest price during the interval        |
| `Low`        | float64 | Lowest price during the interval         |
| `Volume`     | float64 | Total value traded (price * quantity)    |
| `Traded`     | int     | Number of units traded                   |

### Example Request

```bash
# Get all CXPC data for RAT at CI1
curl "https://rest.fnar.net/exchange/cxpc/RAT.CI1"

# Get data since a specific timestamp
curl "https://rest.fnar.net/exchange/cxpc/RAT.CI1/1766000000000"
```

## Other Exchange Endpoints

### Current Exchange Data

```
GET /exchange/{Ticker}.{Exchange}
```

Returns current order book with buy/sell orders:

```json
{
  "MaterialTicker": "RAT",
  "ExchangeCode": "CI1",
  "BuyingOrders": [...],
  "SellingOrders": [...],
  "Price": 100.0,
  "PriceAverage": 98.5,
  ...
}
```

### All Exchange Data

```
GET /exchange/all      # Summary data for all materials
GET /exchange/full     # Full data including order books
```

### CSV Exports

```
GET /csv/prices              # Full price information
GET /csv/cxpc/{Ticker}       # CXPC data for a ticker (all exchanges)
```

## Material Endpoints

```
GET /material/{Ticker}       # Single material info
GET /material/allmaterials   # All materials
```

## Planet Endpoints

```
GET /planet/{PlanetId}       # Single planet
GET /planet/allplanets/full  # All planets with full details
POST /planet/search          # Search with criteria
```

## Recipe Endpoints

```
GET /recipes/{Ticker}              # Recipes producing a material
GET /recipes/building/{Building}   # Recipes for a building
GET /recipes/allrecipes            # All recipes
```

## Building Endpoints

```
GET /building/{Ticker}       # Single building
GET /building/allbuildings   # All buildings with costs/workforce
```

## System Endpoints

```
GET /systemstars             # All star systems with connections
```

## Global Data

```
GET /global/workforceneeds   # Workforce consumption rates
```
