"""Base I/O (daily material input/output) calculation business logic."""

from typing import Any

from prun_mcp.cache import CacheType, get_cache_manager
from prun_mcp.fio import FIONotFoundError, get_fio_client
from prun_mcp.prun_lib import calculate_area_limit
from prun_mcp.utils import fetch_prices
from prun_mcp.prun_lib.exchange import InvalidExchangeError, validate_exchange
from prun_mcp.prun_lib.material_flow import (
    MaterialFlowTracker,
    calculate_material_values,
    process_recipe_flow,
)
from prun_mcp.prun_lib.workforce import (
    WORKFORCE_TYPES,
    aggregate_workforce,
    calculate_workforce_consumption,
    get_workforce_from_building,
)
from prun_mcp.resources.extraction import (
    EXTRACTION_BUILDINGS,
    VALID_EXTRACTION_BUILDINGS,
    calculate_extraction_output,
    get_building_for_resource_type,
)
from prun_mcp.resources.workforce import HABITATION_CAPACITY


class BaseIOValidationError(Exception):
    """Validation error in base I/O calculation."""

    pass


class ProductionValidationError(BaseIOValidationError):
    """Validation error in production entry."""

    def __init__(self, index: int, message: str) -> None:
        self.index = index
        super().__init__(f"Production entry {index}: {message}")


class HabitationValidationError(BaseIOValidationError):
    """Validation error in habitation entry."""

    def __init__(self, index: int, message: str) -> None:
        self.index = index
        super().__init__(f"Habitation entry {index}: {message}")


class ExtractionValidationError(BaseIOValidationError):
    """Validation error in extraction entry."""

    def __init__(self, index: int, message: str) -> None:
        self.index = index
        super().__init__(f"Extraction entry {index}: {message}")


class PermitValidationError(BaseIOValidationError):
    """Validation error for permits."""

    pass


def _validate_production(production: list[dict[str, Any]]) -> None:
    """Validate production entries."""
    if not production:
        raise BaseIOValidationError("No production entries provided")

    for i, entry in enumerate(production):
        if "recipe" not in entry:
            raise ProductionValidationError(i, "missing 'recipe'")
        if "count" not in entry:
            raise ProductionValidationError(i, "missing 'count'")
        if "efficiency" not in entry:
            raise ProductionValidationError(i, "missing 'efficiency'")
        if entry["count"] < 1:
            raise ProductionValidationError(i, "count must be >= 1")
        if entry["efficiency"] <= 0:
            raise ProductionValidationError(i, "efficiency must be > 0")


def _validate_habitation(habitation: list[dict[str, Any]]) -> None:
    """Validate habitation entries."""
    for i, entry in enumerate(habitation):
        if "building" not in entry:
            raise HabitationValidationError(i, "missing 'building'")
        if "count" not in entry:
            raise HabitationValidationError(i, "missing 'count'")
        building = entry["building"].upper()
        if building not in HABITATION_CAPACITY:
            valid_habs = ", ".join(sorted(HABITATION_CAPACITY.keys()))
            raise HabitationValidationError(
                i, f"unknown building '{building}'. Valid: {valid_habs}"
            )


def _validate_extraction(
    extraction: list[dict[str, Any]] | None,
    planet: str | None,
) -> None:
    """Validate extraction entries."""
    if extraction:
        if not planet:
            raise BaseIOValidationError(
                "planet parameter is required when extraction is provided"
            )

        for i, entry in enumerate(extraction):
            if "building" not in entry:
                raise ExtractionValidationError(i, "missing 'building'")
            building = entry["building"].upper()
            if building not in VALID_EXTRACTION_BUILDINGS:
                valid_list = ", ".join(sorted(VALID_EXTRACTION_BUILDINGS))
                raise ExtractionValidationError(
                    i, f"unknown building '{building}'. Valid: {valid_list}"
                )
            if "resource" not in entry:
                raise ExtractionValidationError(i, "missing 'resource'")
            if "count" not in entry:
                raise ExtractionValidationError(i, "missing 'count'")
            if entry["count"] < 1:
                raise ExtractionValidationError(i, "count must be >= 1")
            efficiency = entry.get("efficiency", 1.0)
            if efficiency <= 0:
                raise ExtractionValidationError(i, "efficiency must be > 0")


async def calculate_base_io(
    production: list[dict[str, Any]],
    habitation: list[dict[str, Any]],
    exchange: str,
    permits: int = 1,
    extraction: list[dict[str, Any]] | None = None,
    planet: str | None = None,
) -> dict[str, Any]:
    """Calculate daily material I/O for a base.

    This is the main entry point that handles validation, data fetching,
    and calculation.

    Args:
        production: List of production lines with recipe, count, efficiency.
        habitation: List of habitation buildings with building, count.
        exchange: Exchange code for pricing (e.g., "CI1")
        permits: Number of permits for this base (default: 1)
        extraction: Optional extraction operations with building, resource, count.
        planet: Planet identifier (required if extraction is provided).

    Returns:
        Dict with materials, workforce, habitation, area, and totals.

    Raises:
        InvalidExchangeError: If exchange code is invalid.
        BaseIOValidationError: If validation fails.
        ProductionValidationError: If production entry is invalid.
        HabitationValidationError: If habitation entry is invalid.
        ExtractionValidationError: If extraction entry is invalid.
        PermitValidationError: If permits value is invalid.
    """
    # Validate inputs
    validated_exchange = validate_exchange(exchange)
    if validated_exchange is None:
        raise InvalidExchangeError("Exchange is required")
    exchange = validated_exchange

    _validate_production(production)
    _validate_habitation(habitation)
    _validate_extraction(extraction, planet)

    if permits < 1:
        raise PermitValidationError("permits must be at least 1")

    # Load caches
    recipes_cache = await get_cache_manager().ensure(CacheType.RECIPES)
    buildings_cache = await get_cache_manager().ensure(CacheType.BUILDINGS)
    workforce_cache = await get_cache_manager().ensure(CacheType.WORKFORCE)

    flow_tracker = MaterialFlowTracker()
    total_workforce: dict[str, int] = {wf: 0 for wf in WORKFORCE_TYPES}
    total_area = 0
    errors: list[str] = []

    # Process production lines
    for entry in production:
        recipe_name = entry["recipe"]
        count = entry["count"]
        efficiency = entry["efficiency"]

        recipe_data = recipes_cache.get_recipe_by_name(recipe_name)
        if not recipe_data:
            errors.append(f"Recipe not found: {recipe_name}")
            continue

        building_ticker = recipe_data.get("BuildingTicker", "")
        building = buildings_cache.get_building(building_ticker)
        if not building:
            errors.append(f"Building not found: {building_ticker}")
            continue

        if not process_recipe_flow(recipe_data, count, efficiency, flow_tracker):
            errors.append(f"Invalid recipe duration for {recipe_name}")
            continue

        workforce = get_workforce_from_building(building, count)
        total_workforce = aggregate_workforce(total_workforce, workforce)

        area_cost = building.get("AreaCost", 0)
        total_area += area_cost * count

    # Process extraction
    extraction_errors: list[str] = []
    if extraction and planet:
        client = get_fio_client()
        materials_cache = await get_cache_manager().ensure(CacheType.MATERIALS)

        try:
            planet_data = await client.get_planet(planet)
            planet_resources: dict[str, dict[str, Any]] = {}

            for resource in planet_data.get("Resources", []):
                mat_id = resource.get("MaterialId", "")
                mat_info = materials_cache.get_material(mat_id)
                if mat_info:
                    ticker = mat_info.get("Ticker", "")
                    if ticker:
                        planet_resources[ticker.upper()] = {
                            "type": resource.get("ResourceType", ""),
                            "factor": resource.get("Factor", 0.0),
                        }

            for entry in extraction:
                building_ticker = entry["building"].upper()
                resource_ticker = entry["resource"].upper()
                count = entry["count"]
                efficiency = entry.get("efficiency", 1.0)

                if resource_ticker not in planet_resources:
                    extraction_errors.append(
                        f"Resource {resource_ticker} not found on planet {planet}"
                    )
                    continue

                resource_info = planet_resources[resource_ticker]
                resource_type = resource_info["type"]
                factor = resource_info["factor"]

                expected_building = get_building_for_resource_type(resource_type)
                if expected_building != building_ticker:
                    extraction_errors.append(
                        f"Building {building_ticker} cannot extract "
                        f"{resource_type} resources (use {expected_building})"
                    )
                    continue

                daily_output = calculate_extraction_output(
                    factor=factor,
                    efficiency=efficiency,
                    count=count,
                    resource_type=resource_type,
                )

                flow_tracker.add_output(resource_ticker, daily_output)

                building_spec = EXTRACTION_BUILDINGS[building_ticker]
                for wf_type, worker_count in building_spec["workforce"].items():
                    total_workforce[wf_type] += worker_count * count
                total_area += building_spec["area"] * count

        except FIONotFoundError:
            extraction_errors.append(f"Planet not found: {planet}")

    # Add habitation areas
    for entry in habitation:
        hab_ticker = entry["building"].upper()
        hab_building = buildings_cache.get_building(hab_ticker)
        if hab_building:
            area_cost = hab_building.get("AreaCost", 0)
            total_area += area_cost * entry["count"]

    # Calculate workforce consumables
    workforce_consumption = calculate_workforce_consumption(
        total_workforce, workforce_cache
    )
    flow_tracker.add_consumption(workforce_consumption)

    # Calculate habitation capacity
    hab_capacity: dict[str, int] = {wf: 0 for wf in WORKFORCE_TYPES}
    for entry in habitation:
        building = entry["building"].upper()
        count = entry["count"]
        capacity = HABITATION_CAPACITY.get(building, {})
        for wf_type, cap in capacity.items():
            hab_capacity[wf_type] += cap * count

    hab_validation: list[dict[str, Any]] = []
    hab_sufficient = True
    for wf_type in WORKFORCE_TYPES:
        required = total_workforce[wf_type]
        available = hab_capacity[wf_type]
        if required > 0 or available > 0:
            sufficient = available >= required
            if not sufficient:
                hab_sufficient = False
            hab_validation.append(
                {
                    "workforce_type": wf_type,
                    "required": required,
                    "available": available,
                    "sufficient": sufficient,
                }
            )

    # Fetch prices
    material_flow = flow_tracker.get_flows()
    all_tickers = flow_tracker.get_all_tickers()
    prices = await fetch_prices(all_tickers, exchange)

    # Calculate material values
    materials_output, total_cis_per_day, missing_prices = calculate_material_values(
        material_flow, prices
    )

    area_limit = calculate_area_limit(permits)

    result: dict[str, Any] = {
        "exchange": exchange,
        "materials": materials_output,
        "workforce": {wf: count for wf, count in total_workforce.items() if count > 0},
        "habitation": {
            "validation": hab_validation,
            "sufficient": hab_sufficient,
        },
        "area": {
            "used": total_area,
            "limit": area_limit,
            "permits": permits,
            "remaining": area_limit - total_area,
            "sufficient": total_area <= area_limit,
        },
        "totals": {
            "cis_per_day": round(total_cis_per_day, 2),
        },
    }

    if errors:
        result["errors"] = errors
    if extraction_errors:
        result["extraction_errors"] = extraction_errors
    if missing_prices:
        result["missing_prices"] = missing_prices

    return result
