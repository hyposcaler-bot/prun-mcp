# Exchange Tools

Tools for accessing commodity market prices from the Prosperous Universe game.

## get_exchange_prices

Get current market prices with full order book for material(s) on exchange(s).

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | Yes | Material ticker symbol(s). Single (e.g., "RAT") or comma-separated (e.g., "RAT,BSE,H2O"). |
| `exchange` | string | Yes | Exchange code(s). Single (e.g., "CI1") or comma-separated (e.g., "CI1,NC1"). Valid: AI1, CI1, CI2, IC1, NC1, NC2. |

### Response

Returns TOON-encoded price data including:
- `MaterialTicker`: Material ticker (e.g., "RAT")
- `ExchangeCode`: Exchange code (e.g., "CI1")
- `BuyingOrders`: List of buy orders with CompanyCode, ItemCount, ItemCost
- `SellingOrders`: List of sell orders with CompanyCode, ItemCount, ItemCost
- `Bid`: Highest buy price
- `BidCount`: Number of buy orders
- `Ask`: Lowest sell price
- `AskCount`: Number of sell orders
- `Supply`: Total supply available
- `Demand`: Total demand
- `PriceAverage`: Average traded price
- `High`: Session high
- `Low`: Session low
- `AllTimeHigh`: All-time high price
- `AllTimeLow`: All-time low price

### Examples

**Single material, single exchange:**
```
get_exchange_prices("RAT", "CI1")
# Returns full order book for RAT on CI1 exchange
```

**Multiple materials, single exchange:**
```
get_exchange_prices("RAT,BSE,H2O", "CI1")
# Returns order books for RAT, BSE, and H2O on CI1
```

**Single material, multiple exchanges:**
```
get_exchange_prices("RAT", "CI1,NC1")
# Returns order books for RAT on both CI1 and NC1
```

**Multiple materials, multiple exchanges (cross-product):**
```
get_exchange_prices("RAT,BSE", "CI1,NC1")
# Returns 4 results: RAT.CI1, RAT.NC1, BSE.CI1, BSE.NC1
```

**Partial match (some not found):**
```
get_exchange_prices("RAT,INVALID", "CI1")
# Returns RAT prices, plus not_found: ["INVALID.CI1"]
```

---

## get_exchange_all

Get summary prices for all materials on exchange(s).

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `exchange` | string | Yes | Exchange code(s). Single (e.g., "CI1") or comma-separated (e.g., "CI1,NC1"). Valid: AI1, CI1, CI2, IC1, NC1, NC2. |

### Response

Returns TOON-encoded list of all material prices on the exchange(s) (summary only, no order book).

Each price includes:
- `MaterialTicker`: Material ticker
- `ExchangeCode`: Exchange code
- `Bid`: Highest buy price
- `Ask`: Lowest sell price
- `Supply`: Total supply
- `Demand`: Total demand
- `PriceAverage`: Average price

### Examples

**Single exchange:**
```
get_exchange_all("CI1")
# Returns summary prices for all materials on CI1
```

**Multiple exchanges:**
```
get_exchange_all("CI1,NC1")
# Returns summary prices for all materials on both CI1 and NC1
```

---

## Valid Exchange Codes

| Code | Name |
|------|------|
| AI1 | Antares Imperium Exchange 1 |
| CI1 | Castillo-Ito Mercatus 1 |
| CI2 | Castillo-Ito Mercatus 2 |
| IC1 | Insitor Cooperative Exchange 1 |
| NC1 | Neo-Colonials Exchange 1 |
| NC2 | Neo-Colonials Exchange 2 |

## Notes

- Exchange data is fetched fresh on each call (no caching)
- Multiple tickers and exchanges are fetched in parallel for efficiency
- Use `get_exchange_prices` when you need order book details for specific materials
- Use `get_exchange_all` when you need an overview of all prices on exchange(s)
