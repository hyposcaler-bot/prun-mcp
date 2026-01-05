"""Planet-related MCP tools."""

import logging

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError
from prun_mcp.prun_lib.planets import (
    InvalidLimitError,
    PlanetNotFoundError,
    TooManyResourcesError,
    get_planet_info_async,
    search_planets_async,
)

logger = logging.getLogger(__name__)


@mcp.tool()
async def get_planet_info(planet: str) -> str | list[TextContent]:
    """Get information about a planet by its identifier.

    Args:
        planet: Planet identifier(s). Can be single (e.g., "Katoa")
                or comma-separated (e.g., "Katoa,Montem,Promitor").
                Accepts PlanetId, PlanetNaturalId (e.g., "XK-745b"), or PlanetName.

    Returns:
        TOON-encoded planet data including resources, environment, and other details.
    """
    try:
        result = await get_planet_info_async(planet)
        return toon_encode(result)
    except PlanetNotFoundError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while fetching planet")
        return [TextContent(type="text", text=f"FIO API error: {e}")]


@mcp.tool()
async def search_planets(
    include_resources: str | None = None,
    exclude_resources: str | None = None,
    limit: int = 20,
    top_resources: int = 3,
) -> str | list[TextContent]:
    """Search planets by resource criteria.

    Args:
        include_resources: Comma-separated material tickers that must be present
                          (e.g., "FEO,LST"). Maximum 4 materials.
        exclude_resources: Comma-separated material tickers to exclude
                          (e.g., "H2O,O"). Client-side filtering.
        limit: Maximum planets to return (default 20).
        top_resources: Number of top resources to show per planet (default 3).

    Returns:
        TOON-encoded list of planets with name, id, gravity, temperature,
        fertility, and top resources by factor.
    """
    try:
        result = await search_planets_async(
            include_resources=include_resources,
            exclude_resources=exclude_resources,
            limit=limit,
            top_resources=top_resources,
        )
        return toon_encode(result)
    except InvalidLimitError as e:
        return [TextContent(type="text", text=str(e))]
    except TooManyResourcesError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while searching planets")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
