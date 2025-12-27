# COGM Tools

Tools for calculating Cost of Goods Manufactured (production costs) in Prosperous Universe.

## calculate_cogm

Calculate the cost to produce one unit of a material based on a recipe, including workforce consumables and input materials.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `recipe` | string | Yes | Recipe name (e.g., "1xGRN 1xBEA 1xNUT=>10xRAT"). Use `get_recipe_info` or `search_recipes` to find valid recipe names. |
| `exchange` | string | Yes | Exchange code for pricing (e.g., "CI1"). Valid: AI1, CI1, CI2, IC1, NC1, NC2. |
| `efficiency` | float | No | Production efficiency multiplier (default: 1.0 = 100%) |
| `self_consume` | boolean | No | If true, use produced output to satisfy workforce needs instead of buying from market (default: false) |

### Response

Returns TOON-encoded COGM breakdown including:

- `recipe`: The recipe name
- `building`: Building ticker (e.g., "FP")
- `efficiency`: Efficiency multiplier
- `exchange`: Exchange used for pricing
- `self_consume`: Whether self-consumption is enabled
- `output`: Primary output details
  - `Ticker`: Output material ticker
  - `DailyOutput`: Units produced per day
- `cogm_per_unit`: Cost per output unit
- `breakdown`: Detailed cost breakdown
  - `inputs`: Recipe input costs (Ticker, DailyAmount, Price, DailyCost)
  - `consumables`: Workforce consumable costs (Ticker, WorkforceType, DailyAmount, Price, DailyCost)
- `totals`: Summary costs
  - `daily_input_cost`: Total input costs per day
  - `daily_consumable_cost`: Total workforce consumable costs per day
  - `daily_total_cost`: Total production costs per day
- `self_consumption` (when `self_consume=true`):
  - `consumed`: Map of self-consumed materials and amounts
  - `net_output`: Output after self-consumption
- `missing_prices`: List of materials with no market price (if any)

### Examples

**Basic COGM calculation:**
```
calculate_cogm("1xGRN 1xALG 1xVEG=>10xRAT", "CI1")
# Returns COGM breakdown for RAT production on CI1 prices
```

**With efficiency bonus:**
```
calculate_cogm("1xGRN 1xALG 1xVEG=>10xRAT", "CI1", efficiency=1.33)
# Returns COGM with 133% production efficiency
```

**With self-consumption:**
```
calculate_cogm("1xGRN 1xALG 1xVEG=>10xRAT", "CI1", self_consume=true)
# Uses produced RAT to feed workers instead of buying from market
# Returns lower COGM and net_output after worker consumption
```

---

## Workflow

1. **Find recipes** using `get_recipe_info` or `search_recipes`:
   ```
   get_recipe_info("RAT")
   # Returns all recipes that produce RAT with their RecipeName values
   ```

2. **Calculate COGM** using the exact `RecipeName`:
   ```
   calculate_cogm("1xGRN 1xALG 1xVEG=>10xRAT", "CI1")
   ```

3. **Compare with market price** using `get_exchange_prices`:
   ```
   get_exchange_prices("RAT", "CI1")
   # If Ask > COGM, production is profitable
   ```

---

## Notes

- Workforce consumable rates are fetched from FIO API and cached (24h TTL)
- Recipe and building data are cached (24h TTL)
- Exchange prices are fetched fresh on each call
- The `self_consume` option only applies to recipe **outputs** that match worker consumables
- Input materials (like DW in a COF recipe) are not affected by `self_consume`
