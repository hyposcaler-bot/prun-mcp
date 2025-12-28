"""Planet-related MCP tools."""

import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import MaterialsCache
from prun_mcp.fio import FIOApiError, FIONotFoundError, get_fio_client

logger = logging.getLogger(__name__)

# Shared materials cache for ID→ticker mapping
_materials_cache: MaterialsCache | None = None


def _get_materials_cache() -> MaterialsCache:
    """Get or create the shared materials cache."""
    global _materials_cache
    if _materials_cache is None:
        _materials_cache = MaterialsCache()
    return _materials_cache


async def _ensure_materials_cache() -> MaterialsCache:
    """Ensure the materials cache is populated and valid."""
    cache = _get_materials_cache()
    if not cache.is_valid():
        client = get_fio_client()
        materials = await client.get_all_materials()
        cache.refresh(materials)
    return cache


async def _get_id_to_ticker_map() -> dict[str, str]:
    """Get MaterialId→Ticker mapping from materials cache."""
    cache = await _ensure_materials_cache()
    return {
        mat.get("MaterialId", "").lower(): mat.get("Ticker", "")
        for mat in cache.get_all_materials()
        if mat.get("MaterialId") and mat.get("Ticker")
    }


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

        # Convert Resource MaterialIds to Tickers
        if planet_data:
            id_to_ticker = await _get_id_to_ticker_map()
            for data in planet_data:
                for resource in data.get("Resources", []):
                    mat_id = resource.pop("MaterialId", "").lower()
                    resource["Ticker"] = id_to_ticker.get(mat_id, "?")

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
                          (e.g., "FEO,LST"). Maximum 4 materials. API returns
                          planets containing ALL specified materials.
        exclude_resources: Comma-separated material tickers to exclude
                          (e.g., "H2O,O"). Client-side filtering.
        limit: Maximum planets to return (default 20).
        top_resources: Number of top resources to show per planet,
                      sorted by extraction factor (default 3).

    Returns:
        TOON-encoded list of planets with name, id, gravity, temperature,
        fertility, and top resources by factor.
    """
    # Validate limit
    if limit < 1:
        return [TextContent(type="text", text="limit must be at least 1")]
    if top_resources < 1:
        return [TextContent(type="text", text="top_resources must be at least 1")]

    try:
        client = get_fio_client()

        # Parse include_resources
        include_list: list[str] | None = None
        if include_resources:
            include_list = [t.strip().upper() for t in include_resources.split(",")]
            include_list = [t for t in include_list if t]  # Filter empty strings
            if len(include_list) > 4:
                return [
                    TextContent(
                        type="text",
                        text="Maximum 4 materials allowed for include_resources",
                    )
                ]

        # Parse exclude_resources for client-side filtering
        exclude_set: set[str] = set()
        if exclude_resources:
            exclude_set = {t.strip().upper() for t in exclude_resources.split(",")}
            exclude_set.discard("")  # Remove empty string if present

        # Search planets via API
        planets = await client.search_planets(materials=include_list)

        # Get ID→ticker mapping
        id_to_ticker = await _get_id_to_ticker_map()

        # Process planets
        result: list[dict[str, Any]] = []
        for planet in planets:
            resources = planet.get("Resources", [])
            if not resources:
                continue

            # Convert MaterialIds to tickers and build resource list
            resource_items: list[tuple[str, float]] = []
            has_excluded = False

            for res in resources:
                mat_id = res.get("MaterialId", "")
                factor = res.get("Factor", 0.0)
                ticker = id_to_ticker.get(mat_id.lower(), "?")

                if ticker in exclude_set:
                    has_excluded = True
                    break

                if ticker != "?":
                    resource_items.append((ticker, factor))

            if has_excluded:
                continue

            # Sort by factor descending and take top N
            resource_items.sort(key=lambda x: x[1], reverse=True)
            top_items = resource_items[:top_resources]

            # Format as compact string: "FEO:0.35,LST:0.28"
            resources_str = ",".join(f"{t}:{round(f, 2)}" for t, f in top_items)

            result.append(
                {
                    "name": planet.get("PlanetName", ""),
                    "id": planet.get("PlanetNaturalId", ""),
                    "gravity": round(planet.get("Gravity", 0), 2),
                    "temperature": round(planet.get("Temperature", 0), 1),
                    "fertility": round(planet.get("Fertility", -1), 2),
                    "resources": resources_str,
                }
            )

            if len(result) >= limit:
                break

        return toon_encode(result)

    except FIOApiError as e:
        logger.exception("FIO API error while searching planets")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
