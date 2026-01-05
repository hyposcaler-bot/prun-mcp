"""Building-related MCP tools."""

import logging

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError
from prun_mcp.prun_lib.buildings import (
    BuildingNotFoundError,
    InvalidExpertiseError,
    InvalidWorkforceError,
    get_building_info_async,
    refresh_buildings_cache_async,
    search_buildings_async,
)

logger = logging.getLogger(__name__)


@mcp.tool()
async def get_building_info(ticker: str) -> str | list[TextContent]:
    """Get information about a building by its ticker symbol.

    Args:
        ticker: Building ticker symbol(s). Can be single (e.g., "PP1")
                or comma-separated (e.g., "PP1,HB1,FRM").
                Also accepts BuildingId (32-character hex string).

    Returns:
        TOON-encoded building data including name, area, expertise,
        construction costs, and workforce requirements.
    """
    try:
        result = await get_building_info_async(ticker)
        return toon_encode(result)
    except BuildingNotFoundError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while fetching buildings")
        return [TextContent(type="text", text=f"FIO API error: {e}")]


@mcp.tool()
async def refresh_buildings_cache() -> str:
    """Refresh the buildings cache from FIO API.

    Forces a fresh download of all building data, bypassing the TTL.

    Returns:
        Status message with the number of buildings cached.
    """
    try:
        return await refresh_buildings_cache_async()
    except FIOApiError as e:
        logger.exception("FIO API error while refreshing buildings cache")
        return f"Failed to refresh cache: {e}"


@mcp.tool()
async def search_buildings(
    commodity_tickers: list[str] | None = None,
    expertise: str | None = None,
    workforce: str | None = None,
) -> str | list[TextContent]:
    """Search buildings by construction materials, expertise, or workforce.

    Args:
        commodity_tickers: Material tickers (e.g., ["BSE", "BBH"]).
                          Returns buildings that use ALL specified materials.
        expertise: Expertise type. Valid values: AGRICULTURE, CHEMISTRY,
                   CONSTRUCTION, ELECTRONICS, FOOD_INDUSTRIES, FUEL_REFINING,
                   MANUFACTURING, METALLURGY, RESOURCE_EXTRACTION.
        workforce: Workforce type. Valid values: Pioneers, Settlers,
                   Technicians, Engineers, Scientists.

    Returns:
        TOON-encoded list of matching buildings (Ticker and Name only).
        Use get_building_info for full details. All buildings if no filters.
    """
    try:
        result = await search_buildings_async(
            commodity_tickers=commodity_tickers,
            expertise=expertise,
            workforce=workforce,
        )
        return toon_encode(result)
    except InvalidExpertiseError as e:
        return [TextContent(type="text", text=str(e))]
    except InvalidWorkforceError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while fetching buildings")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
