"""Building cost calculation business logic."""

import math

from prun_mcp.models.domain import (
    BuildingCostResult,
    EnvironmentInfo,
    MaterialCost,
)
from prun_mcp.models.fio import FIOBuilding, FIOPlanet

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


class BuildingCostError(Exception):
    """Error during building cost calculation."""

    pass


class InfertilePlanetError(BuildingCostError):
    """Building requires fertility but planet is infertile."""

    def __init__(self, building_ticker: str) -> None:
        self.building_ticker = building_ticker
        super().__init__(
            f"Building {building_ticker} requires a fertile planet, "
            f"but planet has no fertility"
        )


def get_required_infrastructure_materials(planet: FIOPlanet) -> set[str]:
    """Get the set of infrastructure materials required for a planet.

    This returns the material tickers that would be needed based on the
    planet's environment, without calculating amounts. Useful for knowing
    which prices to fetch.

    Args:
        planet: Planet data with environment information.

    Returns:
        Set of material tickers (e.g., {"MCG", "SEA", "INS"}).
    """
    materials: set[str] = set()

    # Surface type
    if planet.surface:
        materials.add("MCG")
    else:
        materials.add("AEF")

    # Pressure
    if planet.pressure < ENV_THRESHOLDS["low_pressure"]:
        materials.add("SEA")
    elif planet.pressure > ENV_THRESHOLDS["high_pressure"]:
        materials.add("HSE")

    # Gravity
    if planet.gravity < ENV_THRESHOLDS["low_gravity"]:
        materials.add("MGC")
    elif planet.gravity > ENV_THRESHOLDS["high_gravity"]:
        materials.add("BL")

    # Temperature
    if planet.temperature < ENV_THRESHOLDS["cold"]:
        materials.add("INS")
    elif planet.temperature > ENV_THRESHOLDS["hot"]:
        materials.add("TSH")

    return materials


def calculate_infrastructure_costs(area: int, planet: FIOPlanet) -> dict[str, int]:
    """Calculate infrastructure material costs based on planet environment.

    Args:
        area: Building area cost.
        planet: Planet data with environment information.

    Returns:
        Dict mapping material ticker to amount required.
    """
    costs: dict[str, int] = {}

    # Surface type: Rocky uses MCG, Gaseous uses AEF
    if planet.surface:
        costs["MCG"] = area * MCG_PER_AREA_ROCKY
    else:
        costs["AEF"] = math.ceil(area / AEF_DIVISOR_GASEOUS)

    # Pressure
    if planet.pressure < ENV_THRESHOLDS["low_pressure"]:
        costs["SEA"] = area * SEA_PER_AREA_LOW_PRESSURE
    elif planet.pressure > ENV_THRESHOLDS["high_pressure"]:
        costs["HSE"] = 1

    # Gravity
    if planet.gravity < ENV_THRESHOLDS["low_gravity"]:
        costs["MGC"] = 1
    elif planet.gravity > ENV_THRESHOLDS["high_gravity"]:
        costs["BL"] = 1

    # Temperature
    if planet.temperature < ENV_THRESHOLDS["cold"]:
        costs["INS"] = area * INS_PER_AREA_COLD
    elif planet.temperature > ENV_THRESHOLDS["hot"]:
        costs["TSH"] = 1

    return costs


def get_environment_info(planet: FIOPlanet) -> EnvironmentInfo:
    """Classify planet environment conditions.

    Args:
        planet: Planet data with environment information.

    Returns:
        EnvironmentInfo with surface type and condition list.
    """
    conditions: list[str] = []

    # Pressure
    if planet.pressure < ENV_THRESHOLDS["low_pressure"]:
        conditions.append("low-pressure")
    elif planet.pressure > ENV_THRESHOLDS["high_pressure"]:
        conditions.append("high-pressure")

    # Gravity
    if planet.gravity < ENV_THRESHOLDS["low_gravity"]:
        conditions.append("low-gravity")
    elif planet.gravity > ENV_THRESHOLDS["high_gravity"]:
        conditions.append("high-gravity")

    # Temperature
    if planet.temperature < ENV_THRESHOLDS["cold"]:
        conditions.append("cold")
    elif planet.temperature > ENV_THRESHOLDS["hot"]:
        conditions.append("hot")

    return EnvironmentInfo(
        surface_type="rocky" if planet.surface else "gaseous",
        conditions=conditions,
    )


def calculate_building_cost(
    building: FIOBuilding,
    planet: FIOPlanet,
    prices: dict[str, dict[str, float | None]] | None = None,
    exchange: str | None = None,
) -> BuildingCostResult:
    """Calculate complete building cost for a planet.

    Args:
        building: Building data with material requirements.
        planet: Planet data with environment information.
        prices: Optional dict mapping ticker to {"ask": price, "bid": price}.
        exchange: Exchange code if prices are provided.

    Returns:
        BuildingCostResult with all materials and costs.

    Raises:
        InfertilePlanetError: If building requires fertility and planet is infertile.
    """
    # Check fertility requirement for FRM and ORC
    if building.ticker in ("FRM", "ORC") and planet.fertility is None:
        raise InfertilePlanetError(building.ticker)

    # Collect base building costs
    materials: dict[str, int] = {}
    for building_cost in building.building_costs:
        if building_cost.commodity_ticker and building_cost.amount > 0:
            ticker = building_cost.commodity_ticker
            materials[ticker] = materials.get(ticker, 0) + building_cost.amount

    # Add infrastructure costs
    infra_costs = calculate_infrastructure_costs(building.area_cost, planet)
    for ticker, amount in infra_costs.items():
        materials[ticker] = materials.get(ticker, 0) + amount

    # Build material list (sorted alphabetically)
    sorted_tickers = sorted(materials.keys())
    materials_list: list[MaterialCost] = []
    total_cost = 0.0
    missing_prices: list[str] = []

    for ticker in sorted_tickers:
        amount = materials[ticker]
        price: float | None = None
        cost: float | None = None

        if prices and exchange:
            price = prices.get(ticker, {}).get("ask")
            if price is not None:
                price = round(price, 2)
                cost = round(price * amount, 2)
                total_cost += price * amount
            else:
                missing_prices.append(ticker)

        materials_list.append(
            MaterialCost(ticker=ticker, amount=amount, price=price, cost=cost)
        )

    # Get environment info
    environment = get_environment_info(planet)

    return BuildingCostResult(
        building_ticker=building.ticker,
        building_name=building.name,
        planet_name=planet.planet_name,
        planet_id=planet.planet_natural_id,
        area=building.area_cost,
        materials=materials_list,
        environment=environment,
        exchange=exchange,
        total_cost=round(total_cost, 2) if exchange else None,
        missing_prices=missing_prices,
    )
