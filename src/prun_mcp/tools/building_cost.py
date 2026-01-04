"""Building cost calculation tool."""

import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import ensure_buildings_cache
from prun_mcp.fio import FIOApiError, FIONotFoundError, get_fio_client
from prun_mcp.models.domain import BuildingCostResult
from prun_mcp.models.fio import FIOBuilding, FIOPlanet
from prun_mcp.prun_lib import (
    InvalidExchangeError,
    InfertilePlanetError,
    calculate_building_cost as calculate_building_cost_logic,
    get_required_infrastructure_materials,
    validate_exchange,
)
from prun_mcp.utils import fetch_prices

logger = logging.getLogger(__name__)


def format_building_cost_result(result: BuildingCostResult) -> dict[str, Any]:
    """Format BuildingCostResult for TOON output."""
    output: dict[str, Any] = {
        "building": result.building_ticker,
        "planet": f"{result.planet_name} ({result.planet_id})",
        "area": result.area,
    }

    if result.exchange:
        output["exchange"] = result.exchange

    materials_list = []
    for mat in result.materials:
        entry: dict[str, Any] = {
            "material": mat.ticker,
            "amount": mat.amount,
        }
        if result.exchange:
            entry["price"] = mat.price
            entry["cost"] = mat.cost
        materials_list.append(entry)

    output["materials"] = materials_list

    if result.exchange:
        output["total_cost"] = result.total_cost
        if result.missing_prices:
            output["missing_prices"] = result.missing_prices

    output["environment"] = result.environment.description

    return output


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
    try:
        exchange = validate_exchange(exchange)
    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]

    building_ticker = building_ticker.strip().upper()

    try:
        # Get building from cache
        cache = await ensure_buildings_cache()
        building_data = cache.get_building(building_ticker)
        if building_data is None:
            return [TextContent(type="text", text=f"Building not found: {building_ticker}")]
        building = FIOBuilding.model_validate(building_data)

        # Get planet from API
        client = get_fio_client()
        try:
            planet_data = await client.get_planet(planet)
        except FIONotFoundError:
            return [TextContent(type="text", text=f"Planet not found: {planet}")]
        planet_model = FIOPlanet.model_validate(planet_data)

        # Fetch prices if exchange provided
        prices: dict[str, dict[str, float | None]] | None = None
        if exchange:
            building_materials = {c.commodity_ticker for c in building.building_costs}
            infra_materials = get_required_infrastructure_materials(planet_model)
            all_tickers = sorted(building_materials | infra_materials)
            prices = await fetch_prices(all_tickers, exchange)

        # Calculate and format result
        result = calculate_building_cost_logic(
            building=building,
            planet=planet_model,
            prices=prices,
            exchange=exchange,
        )
        return toon_encode(format_building_cost_result(result))

    except InfertilePlanetError as e:
        return [TextContent(type="text", text=str(e))]

    except FIOApiError as e:
        logger.exception("FIO API error")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
