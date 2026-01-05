"""Recipe-related MCP tools."""

import logging

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError
from prun_mcp.prun_lib.recipes import (
    RecipeNotFoundError,
    UnknownBuildingError,
    get_recipe_info_async,
    refresh_recipes_cache_async,
    search_recipes_async,
)

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
        result = await get_recipe_info_async(ticker)
        return toon_encode(result)

    except RecipeNotFoundError as e:
        return [TextContent(type="text", text=str(e))]
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
        result = await search_recipes_async(
            building=building,
            input_tickers=input_tickers,
            output_tickers=output_tickers,
        )
        return toon_encode(result)

    except UnknownBuildingError as e:
        return [TextContent(type="text", text=str(e))]
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
        return await refresh_recipes_cache_async()

    except FIOApiError as e:
        logger.exception("FIO API error while refreshing recipes cache")
        return f"Failed to refresh cache: {e}"
