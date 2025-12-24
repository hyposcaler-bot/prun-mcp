# Recipes Tools

Tools for accessing recipe data from the Prosperous Universe game.

## get_recipe_info

Get recipes that produce a specific material by ticker symbol.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ticker` | string | Yes | Material ticker symbol(s). Single (e.g., "RAT") or comma-separated (e.g., "RAT,BSE,BBH"). |

### Response

Returns TOON-encoded recipe data including:
- `BuildingTicker`: Building that produces this recipe (e.g., "FP", "PP1")
- `RecipeName`: Recipe name showing inputs and outputs (e.g., "1xGRN 1xBEA 1xNUT=>10xRAT")
- `Inputs`: List of input materials with Ticker and Amount
- `Outputs`: List of output materials with Ticker and Amount
- `TimeMs`: Duration in milliseconds

### Examples

**Single material:**
```
get_recipe_info("RAT")
# Returns all recipes that produce RAT (12 different FP recipes)
```

**Multiple materials:**
```
get_recipe_info("RAT,BSE")
# Returns recipes that produce RAT or BSE
```

**Partial match (some not found):**
```
get_recipe_info("RAT,INVALID")
# Returns RAT recipes, plus not_found: ["INVALID"]
```

---

## search_recipes

Search recipes by building, input materials, or output materials.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `building` | string | No | Filter by building ticker (e.g., "PP1", "FP") |
| `input_tickers` | list[string] | No | Filter by input materials (AND logic - must use ALL specified) |
| `output_tickers` | list[string] | No | Filter by output materials (AND logic - must produce ALL specified) |

### Response

Returns TOON-encoded list of matching recipes.

### Examples

**All recipes (no filters):**
```
search_recipes()
```

**By building:**
```
search_recipes(building="FP")
# Returns all Food Processor recipes
```

**By input materials:**
```
search_recipes(input_tickers=["GRN", "BEA"])
# Returns recipes that use BOTH grain and beans as inputs
```

**By output materials:**
```
search_recipes(output_tickers=["RAT"])
# Returns recipes that produce rations
```

**Combined filters:**
```
search_recipes(building="FP", input_tickers=["GRN"], output_tickers=["RAT"])
# Returns FP recipes that use grain to produce rations
```

---

## refresh_recipes_cache

Force refresh the recipes cache from the FIO API, bypassing the 24-hour TTL.

### Parameters

None.

### Response

Returns a status message with the number of recipes cached.

### Example

```
refresh_recipes_cache()
# "Cache refreshed with 1234 recipes"
```
