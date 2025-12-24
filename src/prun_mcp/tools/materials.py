"""Material-related MCP tools."""

import logging

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import MaterialsCache
from prun_mcp.fio import FIOApiError, FIOClient

logger = logging.getLogger(__name__)

# Shared instances
_fio_client: FIOClient | None = None
_materials_cache: MaterialsCache | None = None


def get_fio_client() -> FIOClient:
    """Get or create the shared FIO client."""
    global _fio_client
    if _fio_client is None:
        _fio_client = FIOClient()
    return _fio_client


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
        csv_content = await client.get_all_materials_csv()
        cache.refresh(csv_content)


@mcp.tool()
async def get_material_info(ticker: str) -> str | list[TextContent]:
    """Get information about a material by its ticker symbol.

    Args:
        ticker: Material ticker symbol (e.g., "BSE", "RAT", "H2O")

    Returns:
        TOON-encoded material data including name, category, weight, and volume.
    """
    try:
        await _ensure_cache_populated()
        cache = get_materials_cache()
        data = cache.get_material(ticker.upper())

        if data is None:
            return [TextContent(type="text", text=f"Material '{ticker}' not found")]

        return toon_encode(data)

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
        csv_content = await client.get_all_materials_csv()
        cache.refresh(csv_content)

        return f"Cache refreshed with {cache.material_count()} materials"

    except FIOApiError as e:
        logger.exception("FIO API error while refreshing cache")
        return f"Failed to refresh cache: {e}"
