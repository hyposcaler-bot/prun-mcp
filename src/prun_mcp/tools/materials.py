"""Material-related MCP tools."""

import logging

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError
from prun_mcp.prun_lib.materials import (
    MaterialNotFoundError,
    get_all_materials_async,
    get_material_info_async,
    refresh_materials_cache_async,
)

logger = logging.getLogger(__name__)


@mcp.tool()
async def get_material_info(ticker: str) -> str | list[TextContent]:
    """Get information about a material by its ticker symbol.

    Args:
        ticker: Material ticker symbol(s). Can be single (e.g., "BSE")
                or comma-separated (e.g., "BSE,RAT,H2O").
                Also accepts MaterialId (32-character hex string).

    Returns:
        TOON-encoded material data including name, category, weight, and volume.
    """
    try:
        result = await get_material_info_async(ticker)
        return toon_encode(result)

    except MaterialNotFoundError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while fetching materials")
        return [TextContent(type="text", text=f"FIO API error: {e}")]


@mcp.tool()
async def refresh_materials_cache() -> str:
    """Refresh the materials cache from FIO API.

    Forces a fresh download of all materials data, bypassing the TTL.

    Returns:
        Status message with the number of materials cached.
    """
    try:
        return await refresh_materials_cache_async()

    except FIOApiError as e:
        logger.exception("FIO API error while refreshing cache")
        return f"Failed to refresh cache: {e}"


@mcp.tool()
async def get_all_materials() -> str | list[TextContent]:
    """Get all materials from the cache.

    Returns:
        TOON-encoded list of all materials with their properties.
    """
    try:
        result = await get_all_materials_async()
        return toon_encode(result)

    except FIOApiError as e:
        logger.exception("FIO API error while fetching materials")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
