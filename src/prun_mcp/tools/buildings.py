"""Building-related MCP tools."""

import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import BuildingsCache
from prun_mcp.fio import FIOApiError
from prun_mcp.tools.materials import get_fio_client

logger = logging.getLogger(__name__)

# Shared instance
_buildings_cache: BuildingsCache | None = None


def get_buildings_cache() -> BuildingsCache:
    """Get or create the shared buildings cache."""
    global _buildings_cache
    if _buildings_cache is None:
        _buildings_cache = BuildingsCache()
    return _buildings_cache


async def _ensure_buildings_cache_populated() -> None:
    """Ensure the buildings cache is populated and valid."""
    cache = get_buildings_cache()
    if not cache.is_valid():
        client = get_fio_client()
        buildings = await client.get_all_buildings()
        cache.refresh(buildings)


@mcp.tool()
async def get_building_info(ticker: str) -> str | list[TextContent]:
    """Get information about a building by its ticker symbol.

    Args:
        ticker: Building ticker symbol(s). Can be single (e.g., "PP1")
                or comma-separated (e.g., "PP1,HB1,FRM")

    Returns:
        TOON-encoded building data including name, area, expertise,
        construction costs, and workforce requirements.
    """
    try:
        await _ensure_buildings_cache_populated()
        cache = get_buildings_cache()

        # Parse comma-separated tickers
        tickers = [t.strip().upper() for t in ticker.split(",")]

        buildings = []
        not_found = []

        for t in tickers:
            data = cache.get_building(t)
            if data is None:
                not_found.append(t)
            else:
                buildings.append(data)

        # Build response
        if not buildings and not_found:
            return [
                TextContent(
                    type="text", text=f"Buildings not found: {', '.join(not_found)}"
                )
            ]

        result: dict[str, Any] = {"buildings": buildings}
        if not_found:
            result["not_found"] = not_found

        return toon_encode(result)

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
        cache = get_buildings_cache()
        cache.invalidate()

        client = get_fio_client()
        buildings = await client.get_all_buildings()
        cache.refresh(buildings)

        return f"Cache refreshed with {cache.building_count()} buildings"

    except FIOApiError as e:
        logger.exception("FIO API error while refreshing buildings cache")
        return f"Failed to refresh cache: {e}"


VALID_EXPERTISE = {
    "AGRICULTURE",
    "CHEMISTRY",
    "CONSTRUCTION",
    "ELECTRONICS",
    "FOOD_INDUSTRIES",
    "FUEL_REFINING",
    "MANUFACTURING",
    "METALLURGY",
    "RESOURCE_EXTRACTION",
}

VALID_WORKFORCE = {"Pioneers", "Settlers", "Technicians", "Engineers", "Scientists"}


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
    # Validate expertise
    if expertise and expertise.upper() not in VALID_EXPERTISE:
        valid_list = ", ".join(sorted(VALID_EXPERTISE))
        return [
            TextContent(
                type="text",
                text=f"Invalid expertise '{expertise}'. Valid values: {valid_list}",
            )
        ]

    # Validate workforce
    if workforce and workforce not in VALID_WORKFORCE:
        valid_list = ", ".join(sorted(VALID_WORKFORCE))
        return [
            TextContent(
                type="text",
                text=f"Invalid workforce '{workforce}'. Valid values: {valid_list}",
            )
        ]

    try:
        await _ensure_buildings_cache_populated()
        cache = get_buildings_cache()
        buildings = cache.search_buildings(
            commodity_tickers=commodity_tickers,
            expertise=expertise,
            workforce=workforce,
        )
        return toon_encode(buildings)

    except FIOApiError as e:
        logger.exception("FIO API error while fetching buildings")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
