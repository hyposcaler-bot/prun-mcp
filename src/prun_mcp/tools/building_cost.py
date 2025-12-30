"""Building cost calculation tool."""

import logging
import math
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import BuildingsCache
from prun_mcp.fio import FIOApiError, FIONotFoundError, get_fio_client
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


# Environment thresholds for infrastructure costs
ENV_THRESHOLDS = {
    "low_pressure": 0.25,
    "high_pressure": 2.0,
    "low_gravity": 0.25,
    "high_gravity": 2.5,
    "cold": -25.0,
    "hot": 75.0,
}

# Infrastructure costs per area unit
MCG_PER_AREA_ROCKY = 4  # MCG per area on rocky (surface) planets
AEF_DIVISOR_GASEOUS = 3  # AEF = ceil(area / 3) on gaseous planets
INS_PER_AREA_COLD = 10  # INS per area in cold environments
SEA_PER_AREA_LOW_PRESSURE = 1  # SEA per area in low pressure


def _calculate_infrastructure_costs(
    area: int, planet_data: dict[str, Any]
) -> dict[str, int]:
    """Calculate infrastructure material costs based on planet environment.

    Args:
        area: Building area cost.
        planet_data: Planet data from FIO API.

    Returns:
        Dict mapping material ticker to amount required.
    """
    costs: dict[str, int] = {}

    surface = planet_data.get("Surface", True)
    pressure = planet_data.get("Pressure", 1.0)
    gravity = planet_data.get("Gravity", 1.0)
    temperature = planet_data.get("Temperature", 20.0)

    # Surface type: Rocky uses MCG, Gaseous uses AEF
    if surface:
        costs["MCG"] = area * MCG_PER_AREA_ROCKY
    else:
        costs["AEF"] = math.ceil(area / AEF_DIVISOR_GASEOUS)

    # Pressure
    if pressure < ENV_THRESHOLDS["low_pressure"]:
        costs["SEA"] = area * SEA_PER_AREA_LOW_PRESSURE
    elif pressure > ENV_THRESHOLDS["high_pressure"]:
        costs["HSE"] = 1

    # Gravity
    if gravity < ENV_THRESHOLDS["low_gravity"]:
        costs["MGC"] = 1
    elif gravity > ENV_THRESHOLDS["high_gravity"]:
        costs["BL"] = 1

    # Temperature
    if temperature < ENV_THRESHOLDS["cold"]:
        costs["INS"] = area * INS_PER_AREA_COLD
    elif temperature > ENV_THRESHOLDS["hot"]:
        costs["TSH"] = 1

    return costs


def _get_environment_notes(planet_data: dict[str, Any]) -> list[str]:
    """Get environment description notes for a planet.

    Args:
        planet_data: Planet data from FIO API.

    Returns:
        List of environment condition strings.
    """
    notes: list[str] = []

    surface = planet_data.get("Surface", True)
    pressure = planet_data.get("Pressure", 1.0)
    gravity = planet_data.get("Gravity", 1.0)
    temperature = planet_data.get("Temperature", 20.0)

    # Surface type
    if surface:
        notes.append("rocky")
    else:
        notes.append("gaseous")

    # Pressure
    if pressure < ENV_THRESHOLDS["low_pressure"]:
        notes.append("low-pressure")
    elif pressure > ENV_THRESHOLDS["high_pressure"]:
        notes.append("high-pressure")

    # Gravity
    if gravity < ENV_THRESHOLDS["low_gravity"]:
        notes.append("low-gravity")
    elif gravity > ENV_THRESHOLDS["high_gravity"]:
        notes.append("high-gravity")

    # Temperature
    if temperature < ENV_THRESHOLDS["cold"]:
        notes.append("cold")
    elif temperature > ENV_THRESHOLDS["hot"]:
        notes.append("hot")

    return notes


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

        # Check if soil-based agriculture building on infertile planet
        # Only FRM (Farmstead) and ORC (Orchard) need fertility
        # HYF (Hydroponics Farm) does NOT need fertility
        # Note: negative fertility is valid (reduces efficiency), only None means infertile
        fertility = planet_data.get("Fertility")
        if building_ticker in ("FRM", "ORC") and fertility is None:
            return [
                TextContent(
                    type="text",
                    text=(
                        f"Building {building_ticker} requires a fertile planet, "
                        f"but planet has no fertility"
                    ),
                )
            ]

        # Collect base building costs
        materials: dict[str, int] = {}
        building_costs = building_data.get("BuildingCosts", [])
        for cost in building_costs:
            ticker = cost.get("CommodityTicker", "")
            amount = int(cost.get("Amount", 0))
            if ticker and amount > 0:
                materials[ticker] = materials.get(ticker, 0) + amount

        # Calculate infrastructure costs
        area = int(building_data.get("AreaCost", 0))
        infra_costs = _calculate_infrastructure_costs(area, planet_data)
        for ticker, amount in infra_costs.items():
            materials[ticker] = materials.get(ticker, 0) + amount

        # Get environment notes
        env_notes = _get_environment_notes(planet_data)

        # Build material list (sorted alphabetically)
        sorted_tickers = sorted(materials.keys())

        # Fetch prices if exchange provided
        prices: dict[str, dict[str, float | None]] = {}
        if exchange:
            prices = await fetch_prices(sorted_tickers, exchange)

        # Build output
        planet_name = planet_data.get("PlanetName", "")
        planet_id = planet_data.get("PlanetNaturalId", "")

        result: dict[str, Any] = {
            "building": building_ticker,
            "planet": f"{planet_name} ({planet_id})",
            "area": area,
        }

        if exchange:
            result["exchange"] = exchange

        # Build materials list
        materials_list: list[dict[str, Any]] = []
        total_cost = 0.0
        missing_prices: list[str] = []

        for ticker in sorted_tickers:
            amount = materials[ticker]
            mat_entry: dict[str, Any] = {
                "material": ticker,
                "amount": amount,
            }

            if exchange:
                price = prices.get(ticker, {}).get("ask")
                if price is not None:
                    mat_entry["price"] = round(price, 2)
                    mat_entry["cost"] = round(price * amount, 2)
                    total_cost += price * amount
                else:
                    missing_prices.append(ticker)
                    mat_entry["price"] = None
                    mat_entry["cost"] = None

            materials_list.append(mat_entry)

        result["materials"] = materials_list

        if exchange:
            result["total_cost"] = round(total_cost, 2)
            if missing_prices:
                result["missing_prices"] = missing_prices

        result["environment"] = ", ".join(env_notes)

        return toon_encode(result)

    except FIOApiError as e:
        logger.exception("FIO API error while calculating building cost")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
