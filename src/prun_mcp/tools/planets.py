"""Planet-related MCP tools."""

import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError, FIOClient, FIONotFoundError

logger = logging.getLogger(__name__)

# Shared instance
_fio_client: FIOClient | None = None


def get_fio_client() -> FIOClient:
    """Get or create the shared FIO client."""
    global _fio_client
    if _fio_client is None:
        _fio_client = FIOClient()
    return _fio_client


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
        client = get_fio_client()

        # Parse comma-separated planets
        planets = [p.strip() for p in planet.split(",")]

        planet_data = []
        not_found = []

        for p in planets:
            try:
                data = await client.get_planet(p)
                planet_data.append(data)
            except FIONotFoundError:
                not_found.append(p)

        # Build response
        if not planet_data and not_found:
            return [
                TextContent(
                    type="text", text=f"Planets not found: {', '.join(not_found)}"
                )
            ]

        result: dict[str, Any] = {"planets": planet_data}
        if not_found:
            result["not_found"] = not_found

        return toon_encode(result)

    except FIOApiError as e:
        logger.exception("FIO API error while fetching planet")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
