"""Material-related MCP tools."""

import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import MaterialsCache
from prun_mcp.fio import FIOApiError, get_fio_client

logger = logging.getLogger(__name__)

# Shared materials cache instance
_materials_cache: MaterialsCache | None = None


def get_materials_cache() -> MaterialsCache:
    """Get or create the shared materials cache."""
    global _materials_cache
    if _materials_cache is None:
        _materials_cache = MaterialsCache()
    return _materials_cache


async def _ensure_cache_populated() -> None:
    """Ensure the materials cache is populated and valid."""
    cache = get_materials_cache()
    if not cache.is_valid():
        client = get_fio_client()
        materials = await client.get_all_materials()
        cache.refresh(materials)


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
        await _ensure_cache_populated()
        cache = get_materials_cache()

        # Parse comma-separated identifiers
        identifiers = [t.strip() for t in ticker.split(",")]

        materials = []
        not_found = []

        for identifier in identifiers:
            data = cache.get_material(identifier)
            if data is None:
                not_found.append(identifier)
            else:
                materials.append(data)

        # Build response
        if not materials and not_found:
            return [
                TextContent(
                    type="text", text=f"Materials not found: {', '.join(not_found)}"
                )
            ]

        result: dict[str, Any] = {"materials": materials}
        if not_found:
            result["not_found"] = not_found

        return toon_encode(result)

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
        cache = get_materials_cache()
        cache.invalidate()

        client = get_fio_client()
        materials = await client.get_all_materials()
        cache.refresh(materials)

        return f"Cache refreshed with {cache.material_count()} materials"

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
        await _ensure_cache_populated()
        cache = get_materials_cache()
        materials = cache.get_all_materials()
        return toon_encode(materials)

    except FIOApiError as e:
        logger.exception("FIO API error while fetching materials")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
