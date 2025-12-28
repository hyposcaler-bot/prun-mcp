# Market Analysis Tools

Tools for analyzing market conditions, order book depth, price history, and trade fill costs.

## get_market_summary

Get a quick market snapshot with actionable warnings.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | Yes | Material ticker symbol(s). Single (e.g., "RAT") or comma-separated (e.g., "RAT,COF,SF"). |
| `exchange` | string | Yes | Exchange code (e.g., "CI1"). Single exchange only. Valid: AI1, CI1, CI2, IC1, NC1, NC2. |

### Response

Returns **plain text** market summary with:
- Bid/Ask prices with depth at best price
- Spread (absolute and percentage)
- Supply/Demand ratio and market type
- Market Maker (MM) buy/sell prices (if present)
- Actionable warnings for trading decisions

### Warnings Generated

- Wide spread (>5%) — consider limit orders
- No buy/sell orders — cannot execute at market
- Thin depth (<50 units) — slippage warning
- Heavy supply/demand pressure (>3x imbalance)
- Price near MM ceiling (within 5%) — limited upside
- Price near MM floor (within 5%) — limited downside

### Examples

**Single ticker:**
```
get_market_summary("RAT", "CI1")

# Output:
RAT on CI1:
Bid: 163 (2,492 units) | Ask: 174 (586 units)
Spread: 11 (6.7%) | Mid: 168.50
Supply: 67,081 | Demand: 380,930 | Ratio: 0.2x (buyer's market)
MM: Buy 32 | Sell 176

Warnings:
• Wide spread (6.7% > 5%) — consider limit orders over market orders
• Heavy demand pressure (0.18x) — expect upward price pressure
• Price near MM ceiling (174 vs 176) — limited upside
```

**Multiple tickers:**
```
get_market_summary("RAT,COF,SF", "CI1")
# Returns sections separated by ---, with ticker-prefixed warnings
```

---

## analyze_fill_cost

Calculate expected cost/proceeds for a specific quantity by walking the order book.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | Yes | Material ticker symbol (e.g., "RAT"). **Single ticker only.** |
| `exchange` | string | Yes | Exchange code (e.g., "CI1"). Valid: AI1, CI1, CI2, IC1, NC1, NC2. |
| `quantity` | integer | Yes | Number of units to buy or sell. |
| `direction` | string | Yes | "buy" or "sell". |

### Response

Returns **TOON-encoded** fill analysis including:
- `can_fill`: Whether full quantity is available
- `fill_quantity`: Units that can be filled
- `vwap`: Volume-weighted average price
- `total_cost`: Total cost/proceeds
- `slippage_from_best`: Absolute slippage from best price
- `slippage_pct`: Slippage as percentage
- `fills`: Breakdown by price level
- `recommendations`: Limit price suggestions

### Examples

```
analyze_fill_cost("RAT", "CI1", 1000, "buy")

# Returns fill analysis showing:
# - Best price, worst price consumed
# - VWAP for the order
# - Slippage from best available price
# - Recommendations for limit orders at different fill percentages
```

---

## get_price_history_summary

Compare current market conditions to historical norms.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | Yes | Material ticker symbol(s). Single or comma-separated. |
| `exchange` | string | Yes | Exchange code (e.g., "CI1"). Single exchange only. |
| `days` | integer | No | Lookback period in days. Valid: 1-30. Default: 7. |

### Response

Returns **plain text** historical comparison with:
- Current mid price and spread
- Historical average, high, low
- Volume statistics
- Insights comparing current to historical prices

### Insights Generated

- Price vs historical average (fair value, above/below)
- Low volume warnings for illiquid markets

### Examples

```
get_price_history_summary("RAT", "CI1", 7)

# Output:
RAT on CI1 (7-day history):

Current: 168.5 mid | Spread: 6.7%
Historical: avg 165.2 | range 158–175
Volume: ~2,500/day (17,500 total, 7 days)

Insights:
• Current price (168.5) is 2.0% above avg — slightly elevated
```

---

## get_order_book_depth

Get full order book in TOON tabular format.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | Yes | Material ticker symbol(s). Single or comma-separated. |
| `exchange` | string | Yes | Exchange code (e.g., "CI1"). Single exchange only. |
| `side` | string | No | "buy" (bids), "sell" (asks), or "both". Default: "both". |
| `levels` | integer | No | Max price levels per side. Valid: 1-100. Default: 20. Capped to 10 for multi-ticker. |

### Response

Returns **TOON-encoded** order book with:
- Aggregated price levels (orders at same price combined)
- Cumulative units and VWAP at each level
- Cumulative cost (sells) or proceeds (buys)
- Summary with spread, total depth, and MM prices (if present)

### Examples

**Single ticker:**
```
get_order_book_depth("RAT", "CI1", "both", 10)

# Returns up to 10 levels each side with cumulative calculations
```

**Multiple tickers:**
```
get_order_book_depth("RAT,COF", "CI1")

# Returns order_books array, levels capped at 10
```

---

## get_price_history

Get historical price data in TOON tabular format.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | Yes | Material ticker symbol(s). Single or comma-separated. |
| `exchange` | string | Yes | Exchange code (e.g., "CI1"). Single exchange only. |
| `days` | integer | No | Lookback period in days. Valid: 1-30. Default: 7. |

### Response

Returns **TOON-encoded** time series with:
- `daily`: Array of OHLCV candles (most recent first)
  - `date`: ISO date string
  - `open`, `high`, `low`, `close`: Price data
  - `volume`: Units traded
- `summary`: Period statistics
  - `avg_price`, `high`, `low`
  - `total_volume`, `avg_daily_volume`
  - `price_change`, `price_change_pct`

### Examples

```
get_price_history("RAT", "CI1", 7)

# Returns 7 days of daily OHLCV data with summary statistics
```

---

## Tool Comparison

| Tool | Output Format | Multi-ticker | Use Case |
|------|---------------|--------------|----------|
| `get_market_summary` | Plain text | Yes | Quick market overview with warnings |
| `analyze_fill_cost` | TOON | No | Pre-trade slippage analysis |
| `get_price_history_summary` | Plain text | Yes | Is current price good/bad? |
| `get_order_book_depth` | TOON | Yes (10 level cap) | Detailed order book analysis |
| `get_price_history` | TOON | Yes | Historical trend analysis |

## Notes

- All tools fetch fresh data on each call (no caching)
- Multi-ticker requests are fetched in parallel for efficiency
- Plain text tools are designed for quick human-readable insights
- TOON tools provide structured data for further analysis
- Use `get_market_summary` for quick checks before trading
- Use `analyze_fill_cost` before placing large orders to understand slippage
