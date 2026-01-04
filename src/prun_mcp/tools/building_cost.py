"""Building cost calculation tool."""

import logging

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import BuildingsCache
from prun_mcp.fio import FIOApiError, FIONotFoundError, get_fio_client
from prun_mcp.models.fio import FIOBuilding, FIOPlanet
from prun_mcp.prun_lib.building import InfertilePlanetError
from prun_mcp.prun_lib.building import (
    calculate_building_cost as calculate_building_cost_logic,
)
from prun_mcp.resources.exchanges import VALID_EXCHANGES
from prun_mcp.utils import fetch_prices

logger = logging.getLogger(__name__)

# Shared instance
_buildings_cache: BuildingsCache | None = None


def get_buildings_cache() -> BuildingsCache:
    """Get or create the shared buildings cache."""
    global _buildings_cache
    if _buildings_cache is None:
        _buildings_cache = BuildingsCache()
    return _buildings_cache


async def _ensure_buildings_cache_populated() -> None:
    """Ensure the buildings cache is populated and valid."""
    cache = get_buildings_cache()
    if not cache.is_valid():
        client = get_fio_client()
        buildings = await client.get_all_buildings()
        cache.refresh(buildings)


@mcp.tool()
async def calculate_building_cost(
    building_ticker: str,
    planet: str,
    exchange: str | None = None,
) -> str | list[TextContent]:
    """Calculate total cost to build a building on a planet.

    Calculates the complete material requirements including base building
    costs and infrastructure materials based on planetary environment
    (surface type, pressure, gravity, temperature).

    Args:
        building_ticker: Building ticker (e.g., "FP", "HB1", "FRM").
        planet: Planet identifier (name, natural ID, or planet ID).
        exchange: Optional exchange code for cost calculation (e.g., "CI1").
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.

    Returns:
        TOON-encoded breakdown of materials including base costs
        and infrastructure requirements based on planet environment.
        If exchange is provided, includes price and cost per material.
    """
    building_ticker = building_ticker.strip().upper()

    # Validate exchange if provided
    if exchange:
        exchange = exchange.strip().upper()
        if exchange not in VALID_EXCHANGES:
            valid_list = ", ".join(sorted(VALID_EXCHANGES))
            return [
                TextContent(
                    type="text",
                    text=f"Invalid exchange: {exchange}. Valid: {valid_list}",
                )
            ]

    try:
        # Get building data from cache
        await _ensure_buildings_cache_populated()
        cache = get_buildings_cache()
        building_data = cache.get_building(building_ticker)

        if building_data is None:
            return [
                TextContent(
                    type="text",
                    text=f"Building not found: {building_ticker}",
                )
            ]

        # Parse building data into Pydantic model
        building = FIOBuilding.model_validate(building_data)

        # Get planet data from FIO API
        client = get_fio_client()
        try:
            planet_data = await client.get_planet(planet)
        except FIONotFoundError:
            return [
                TextContent(
                    type="text",
                    text=f"Planet not found: {planet}",
                )
            ]

        # Parse planet data into Pydantic model
        planet_model = FIOPlanet.model_validate(planet_data)

        # Fetch prices if exchange provided
        prices: dict[str, dict[str, float | None]] | None = None
        if exchange:
            # Get all material tickers for price fetch
            material_tickers = {
                cost.commodity_ticker for cost in building.building_costs
            }
            # Infrastructure materials will be added by business logic,
            # but we need to fetch their prices too. For simplicity,
            # fetch common infrastructure materials.
            infra_materials = {"MCG", "AEF", "SEA", "HSE", "MGC", "BL", "INS", "TSH"}
            all_tickers = sorted(material_tickers | infra_materials)
            prices = await fetch_prices(all_tickers, exchange)

        # Call business logic
        result = calculate_building_cost_logic(
            building=building,
            planet=planet_model,
            prices=prices,
            exchange=exchange,
        )

        # Convert to output format and encode as TOON
        return toon_encode(result.to_output_dict())

    except InfertilePlanetError as e:
        return [TextContent(type="text", text=str(e))]

    except FIOApiError as e:
        logger.exception("FIO API error while calculating building cost")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
