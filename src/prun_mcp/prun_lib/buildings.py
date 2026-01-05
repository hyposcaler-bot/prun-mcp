"""Buildings business logic."""

from typing import Any

from prun_mcp.cache import ensure_buildings_cache, get_buildings_cache
from prun_mcp.fio import get_fio_client
from prun_mcp.models.fio import FIOBuildingFull, camel_to_title
from prun_mcp.prun_lib.exceptions import BuildingNotFoundError

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


class BuildingsError(Exception):
    """Base error for buildings operations."""

    pass


class InvalidExpertiseError(BuildingsError):
    """Invalid expertise type."""

    def __init__(self, expertise: str) -> None:
        self.expertise = expertise
        valid_list = ", ".join(sorted(VALID_EXPERTISE))
        super().__init__(f"Invalid expertise '{expertise}'. Valid values: {valid_list}")


class InvalidWorkforceError(BuildingsError):
    """Invalid workforce type."""

    def __init__(self, workforce: str) -> None:
        self.workforce = workforce
        valid_list = ", ".join(sorted(VALID_WORKFORCE))
        super().__init__(f"Invalid workforce '{workforce}'. Valid values: {valid_list}")


async def get_building_info_async(ticker: str) -> dict[str, Any]:
    """Get information about a building by its ticker symbol.

    Args:
        ticker: Building ticker symbol(s). Single or comma-separated.
                Also accepts BuildingId (32-character hex string).

    Returns:
        Dict with 'buildings' list and optional 'not_found' list.

    Raises:
        BuildingNotFoundError: If all requested buildings are not found.
    """
    cache = await ensure_buildings_cache()
    identifiers = [t.strip() for t in ticker.split(",")]

    buildings: list[dict[str, Any]] = []
    not_found: list[str] = []

    for identifier in identifiers:
        data = cache.get_building(identifier)
        if data is None:
            not_found.append(identifier)
        else:
            building = FIOBuildingFull.model_validate(data)
            buildings.append(building.model_dump(by_alias=True))

    if not buildings and not_found:
        raise BuildingNotFoundError(not_found)

    result: dict[str, Any] = {"buildings": buildings}
    if not_found:
        result["not_found"] = not_found

    return result


async def refresh_buildings_cache_async() -> str:
    """Refresh the buildings cache from FIO API.

    Forces a fresh download of all building data, bypassing the TTL.

    Returns:
        Status message with the number of buildings cached.
    """
    cache = get_buildings_cache()
    cache.invalidate()

    client = get_fio_client()
    buildings = await client.get_all_buildings()
    cache.refresh(buildings)

    return f"Cache refreshed with {cache.building_count()} buildings"


async def search_buildings_async(
    commodity_tickers: list[str] | None = None,
    expertise: str | None = None,
    workforce: str | None = None,
) -> dict[str, Any]:
    """Search buildings by construction materials, expertise, or workforce.

    Args:
        commodity_tickers: Material tickers. Returns buildings using ALL specified.
        expertise: Expertise type to filter by.
        workforce: Workforce type to filter by.

    Returns:
        Dict with 'buildings' list containing matching buildings.

    Raises:
        InvalidExpertiseError: If expertise is invalid.
        InvalidWorkforceError: If workforce is invalid.
    """
    if expertise and expertise.upper() not in VALID_EXPERTISE:
        raise InvalidExpertiseError(expertise)

    if workforce and workforce not in VALID_WORKFORCE:
        raise InvalidWorkforceError(workforce)

    cache = await ensure_buildings_cache()
    buildings = cache.search_buildings(
        commodity_tickers=commodity_tickers,
        expertise=expertise,
        workforce=workforce,
    )

    result_buildings: list[dict[str, str]] = [
        {"Ticker": b.get("Ticker", ""), "Name": camel_to_title(b.get("Name", ""))}
        for b in buildings
    ]

    return {"buildings": result_buildings}
