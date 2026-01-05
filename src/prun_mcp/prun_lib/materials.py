"""Materials business logic."""

from typing import Any

from prun_mcp.cache import CacheType, get_cache_manager
from prun_mcp.fio import get_fio_client
from prun_mcp.models.fio import FIOMaterial
from prun_mcp.prun_lib.exceptions import MaterialNotFoundError


async def get_material_info_async(ticker: str) -> dict[str, Any]:
    """Get information about a material by its ticker symbol.

    Args:
        ticker: Material ticker symbol(s). Single or comma-separated.
                Also accepts MaterialId (32-character hex string).

    Returns:
        Dict with 'materials' list and optional 'not_found' list.

    Raises:
        MaterialNotFoundError: If all requested materials are not found.
    """
    cache = await get_cache_manager().ensure(CacheType.MATERIALS)
    identifiers = [t.strip() for t in ticker.split(",")]

    materials: list[dict[str, Any]] = []
    not_found: list[str] = []

    for identifier in identifiers:
        data = cache.get_material(identifier)
        if data is None:
            not_found.append(identifier)
        else:
            material = FIOMaterial.model_validate(data)
            materials.append(material.model_dump(by_alias=True))

    if not materials and not_found:
        raise MaterialNotFoundError(not_found)

    result: dict[str, Any] = {"materials": materials}
    if not_found:
        result["not_found"] = not_found

    return result


async def refresh_materials_cache_async() -> str:
    """Refresh the materials cache from FIO API.

    Forces a fresh download of all materials data, bypassing the TTL.

    Returns:
        Status message with the number of materials cached.
    """
    cache = get_cache_manager().get(CacheType.MATERIALS)
    cache.invalidate()

    client = get_fio_client()
    materials = await client.get_all_materials()
    cache.refresh(materials)

    return f"Cache refreshed with {cache.material_count()} materials"


async def get_all_materials_async() -> dict[str, Any]:
    """Get all materials from the cache.

    Returns:
        Dict with 'materials' list containing all materials.
    """
    cache = await get_cache_manager().ensure(CacheType.MATERIALS)
    all_materials = cache.get_all_materials()

    materials: list[dict[str, Any]] = []
    for m in all_materials:
        material = FIOMaterial.model_validate(m)
        materials.append(material.model_dump(by_alias=True))

    return {"materials": materials}
