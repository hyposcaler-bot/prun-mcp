"""Planets business logic."""

from typing import Any

from prun_mcp.cache import CacheType, get_cache_manager
from prun_mcp.fio import FIONotFoundError, get_fio_client
from prun_mcp.prun_lib.exceptions import PlanetNotFoundError


class PlanetsError(Exception):
    """Base error for planets operations."""

    pass


class InvalidLimitError(PlanetsError):
    """Invalid limit value."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class TooManyResourcesError(PlanetsError):
    """Too many resources specified."""

    def __init__(self) -> None:
        super().__init__("Maximum 4 materials allowed for include_resources")


async def _get_id_to_ticker_map() -> dict[str, str]:
    """Get MaterialId→Ticker mapping from materials cache."""
    cache = await get_cache_manager().ensure(CacheType.MATERIALS)
    return {
        mat.get("MaterialId", "").lower(): mat.get("Ticker", "")
        for mat in cache.get_all_materials()
        if mat.get("MaterialId") and mat.get("Ticker")
    }


async def get_planet_info_async(planet: str) -> dict[str, Any]:
    """Get information about a planet by its identifier.

    Args:
        planet: Planet identifier(s). Single or comma-separated.
                Accepts PlanetId, PlanetNaturalId, or PlanetName.

    Returns:
        Dict with 'planets' list and optional 'not_found' list.

    Raises:
        PlanetNotFoundError: If all requested planets are not found.
    """
    client = get_fio_client()
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

    if not planet_data and not_found:
        raise PlanetNotFoundError(not_found)

    result: dict[str, Any] = {"planets": planet_data}
    if not_found:
        result["not_found"] = not_found

    return result


async def search_planets_async(
    include_resources: str | None = None,
    exclude_resources: str | None = None,
    limit: int = 20,
    top_resources: int = 3,
) -> list[dict[str, Any]]:
    """Search planets by resource criteria.

    Args:
        include_resources: Comma-separated material tickers that must be present.
                          Maximum 4 materials.
        exclude_resources: Comma-separated material tickers to exclude.
        limit: Maximum planets to return (default 20).
        top_resources: Number of top resources to show per planet (default 3).

    Returns:
        List of planets with name, id, gravity, temperature, fertility, and resources.

    Raises:
        InvalidLimitError: If limit or top_resources is invalid.
        TooManyResourcesError: If more than 4 include resources specified.
    """
    if limit < 1:
        raise InvalidLimitError("limit must be at least 1")
    if top_resources < 1:
        raise InvalidLimitError("top_resources must be at least 1")

    client = get_fio_client()

    include_list: list[str] | None = None
    if include_resources:
        include_list = [t.strip().upper() for t in include_resources.split(",")]
        include_list = [t for t in include_list if t]
        if len(include_list) > 4:
            raise TooManyResourcesError()

    exclude_set: set[str] = set()
    if exclude_resources:
        exclude_set = {t.strip().upper() for t in exclude_resources.split(",")}
        exclude_set.discard("")

    planets = await client.search_planets(materials=include_list)
    id_to_ticker = await _get_id_to_ticker_map()

    result: list[dict[str, Any]] = []
    for planet in planets:
        resources = planet.get("Resources", [])
        if not resources:
            continue

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

        resource_items.sort(key=lambda x: x[1], reverse=True)
        top_items = resource_items[:top_resources]
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

    return result
