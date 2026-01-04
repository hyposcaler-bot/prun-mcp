"""Material-related MCP tools."""

import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import ensure_materials_cache, get_materials_cache
from prun_mcp.fio import FIOApiError, get_fio_client
from prun_mcp.models.fio import FIOMaterial

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
        cache = await ensure_materials_cache()
        identifiers = [t.strip() for t in ticker.split(",")]

        materials: list[dict[str, Any]] = []
        not_found: list[str] = []

        for identifier in identifiers:
            data = cache.get_material(identifier)
            if data is None:
                not_found.append(identifier)
            else:
                # Parse into Pydantic model for validation and prettification
                material = FIOMaterial.model_validate(data)
                materials.append(material.model_dump(by_alias=True))

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
        cache = await ensure_materials_cache()
        all_materials = cache.get_all_materials()

        # Parse each material for validation and prettification
        materials: list[dict[str, Any]] = []
        for m in all_materials:
            material = FIOMaterial.model_validate(m)
            materials.append(material.model_dump(by_alias=True))

        return toon_encode({"materials": materials})

    except FIOApiError as e:
        logger.exception("FIO API error while fetching materials")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
