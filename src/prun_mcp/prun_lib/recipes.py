"""Recipes business logic."""

from typing import Any


class RecipesError(Exception):
    """Base error for recipes operations."""

    pass


class RecipeNotFoundError(RecipesError):
    """No recipes found for the given criteria."""

    def __init__(self, tickers: list[str]) -> None:
        self.tickers = tickers
        super().__init__(f"No recipes found that produce: {', '.join(tickers)}")


class UnknownBuildingError(RecipesError):
    """Building ticker not found."""

    def __init__(self, building: str) -> None:
        self.building = building
        super().__init__(f"Unknown building ticker: {building}")


async def get_recipe_info_async(ticker: str) -> dict[str, Any]:
    """Get recipes that produce a specific material.

    Args:
        ticker: Material ticker symbol(s). Single or comma-separated.

    Returns:
        Dict with 'recipes' list and optional 'not_found' list.

    Raises:
        RecipeNotFoundError: If no recipes found for any of the tickers.
    """
    from prun_mcp.cache import ensure_recipes_cache
    from prun_mcp.models.fio import FIORecipe

    cache = await ensure_recipes_cache()
    tickers = [t.strip().upper() for t in ticker.split(",")]

    recipes: list[dict[str, Any]] = []
    not_found: list[str] = []

    for t in tickers:
        t_recipes = cache.get_recipes_by_output(t)
        if not t_recipes:
            not_found.append(t)
        else:
            for r in t_recipes:
                recipe = FIORecipe.model_validate(r)
                recipes.append(recipe.model_dump(by_alias=True))

    if not recipes and not_found:
        raise RecipeNotFoundError(not_found)

    result: dict[str, Any] = {"recipes": recipes}
    if not_found:
        result["not_found"] = not_found

    return result


async def search_recipes_async(
    building: str | None = None,
    input_tickers: list[str] | None = None,
    output_tickers: list[str] | None = None,
) -> dict[str, Any]:
    """Search recipes by building, input materials, or output materials.

    Args:
        building: Building ticker to filter by (e.g., "PP1", "FP").
        input_tickers: Input material tickers. Returns recipes using ALL specified.
        output_tickers: Output material tickers. Returns recipes producing ALL specified.

    Returns:
        Dict with 'recipes' list containing matching recipes.

    Raises:
        UnknownBuildingError: If building ticker is not found.
    """
    from prun_mcp.cache import ensure_buildings_cache, ensure_recipes_cache
    from prun_mcp.models.fio import FIORecipe

    # Validate building ticker if provided
    if building:
        buildings_cache = await ensure_buildings_cache()
        building_upper = building.upper()
        if not buildings_cache.get_building(building_upper):
            raise UnknownBuildingError(building_upper)

    cache = await ensure_recipes_cache()
    raw_recipes = cache.search_recipes(
        building=building,
        input_tickers=input_tickers,
        output_tickers=output_tickers,
    )

    recipes: list[dict[str, Any]] = []
    for r in raw_recipes:
        recipe = FIORecipe.model_validate(r)
        recipes.append(recipe.model_dump(by_alias=True))

    return {"recipes": recipes}


async def refresh_recipes_cache_async() -> str:
    """Refresh the recipes cache from FIO API.

    Forces a fresh download of all recipe data, bypassing the TTL.

    Returns:
        Status message with the number of recipes cached.
    """
    from prun_mcp.cache import get_recipes_cache
    from prun_mcp.fio import get_fio_client

    cache = get_recipes_cache()
    cache.invalidate()

    client = get_fio_client()
    recipes = await client.get_all_recipes()
    cache.refresh(recipes)

    return f"Cache refreshed with {cache.recipe_count()} recipes"
