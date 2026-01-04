"""Recipe-related MCP tools."""

import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import (
    ensure_buildings_cache,
    ensure_recipes_cache,
    get_recipes_cache,
)
from prun_mcp.fio import FIOApiError, get_fio_client
from prun_mcp.utils import prettify_names

logger = logging.getLogger(__name__)


@mcp.tool()
async def get_recipe_info(ticker: str) -> str | list[TextContent]:
    """Get recipes that produce a specific material.

    Args:
        ticker: Material ticker symbol(s). Can be single (e.g., "BSE")
                or comma-separated (e.g., "BSE,RAT,H2O").

    Returns:
        TOON-encoded recipe data including building, inputs, outputs, and duration.
    """
    try:
        cache = await ensure_recipes_cache()
        tickers = [t.strip().upper() for t in ticker.split(",")]

        recipes: list[dict[str, Any]] = []
        not_found = []

        for t in tickers:
            t_recipes = cache.get_recipes_by_output(t)
            if not t_recipes:
                not_found.append(t)
            else:
                recipes.extend(t_recipes)

        if not recipes and not_found:
            return [
                TextContent(
                    type="text",
                    text=f"No recipes found that produce: {', '.join(not_found)}",
                )
            ]

        result: dict[str, Any] = {"recipes": recipes}
        if not_found:
            result["not_found"] = not_found

        return toon_encode(prettify_names(result))

    except FIOApiError as e:
        logger.exception("FIO API error while fetching recipes")
        return [TextContent(type="text", text=f"FIO API error: {e}")]


@mcp.tool()
async def search_recipes(
    building: str | None = None,
    input_tickers: list[str] | None = None,
    output_tickers: list[str] | None = None,
) -> str | list[TextContent]:
    """Search recipes by building, input materials, or output materials.

    Args:
        building: Building ticker to filter by (e.g., "PP1", "FP").
        input_tickers: Input material tickers (e.g., ["GRN", "BEA"]).
                       Returns recipes that use ALL specified materials.
        output_tickers: Output material tickers (e.g., ["RAT"]).
                        Returns recipes that produce ALL specified materials.

    Returns:
        TOON-encoded list of matching recipes.
    """
    try:
        # Validate building ticker if provided
        if building:
            buildings_cache = await ensure_buildings_cache()
            building_upper = building.upper()
            if not buildings_cache.get_building(building_upper):
                return [
                    TextContent(
                        type="text",
                        text=f"Unknown building ticker: {building_upper}",
                    )
                ]

        cache = await ensure_recipes_cache()
        recipes = cache.search_recipes(
            building=building,
            input_tickers=input_tickers,
            output_tickers=output_tickers,
        )
        return toon_encode(prettify_names({"recipes": recipes}))

    except FIOApiError as e:
        logger.exception("FIO API error while fetching recipes")
        return [TextContent(type="text", text=f"FIO API error: {e}")]


@mcp.tool()
async def refresh_recipes_cache() -> str:
    """Refresh the recipes cache from FIO API.

    Forces a fresh download of all recipe data, bypassing the TTL.

    Returns:
        Status message with the number of recipes cached.
    """
    try:
        cache = get_recipes_cache()
        cache.invalidate()

        client = get_fio_client()
        recipes = await client.get_all_recipes()
        cache.refresh(recipes)

        return f"Cache refreshed with {cache.recipe_count()} recipes"

    except FIOApiError as e:
        logger.exception("FIO API error while refreshing recipes cache")
        return f"Failed to refresh cache: {e}"
