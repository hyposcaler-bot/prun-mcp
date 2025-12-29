"""Permit daily I/O calculator tool."""

import asyncio
import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import BuildingsCache, MaterialsCache, RecipesCache, WorkforceCache
from prun_mcp.fio import FIOApiError, FIONotFoundError, get_fio_client
from prun_mcp.resources.exchanges import VALID_EXCHANGES
from prun_mcp.resources.extraction import (
    EXTRACTION_BUILDINGS,
    VALID_EXTRACTION_BUILDINGS,
    calculate_extraction_output,
    get_building_for_resource_type,
)
from prun_mcp.resources.workforce import HABITATION_CAPACITY, WORKFORCE_TYPES
from prun_mcp.utils import fetch_prices, prettify_names

logger = logging.getLogger(__name__)

MS_PER_DAY = 24 * 60 * 60 * 1000  # Milliseconds per day


def calculate_area_limit(permits: int) -> int:
    """Calculate area limit for given number of permits.

    Args:
        permits: Number of permits used for this base.

    Returns:
        Total area available (1st permit = 500, each additional = +250).
    """
    if permits <= 0:
        return 0
    # 1st permit = 500, each additional = +250
    return 500 + max(0, permits - 1) * 250


# Shared cache instances
_buildings_cache: BuildingsCache | None = None
_recipes_cache: RecipesCache | None = None
_workforce_cache: WorkforceCache | None = None
_materials_cache: MaterialsCache | None = None


def get_buildings_cache() -> BuildingsCache:
    """Get or create the shared buildings cache."""
    global _buildings_cache
    if _buildings_cache is None:
        _buildings_cache = BuildingsCache()
    return _buildings_cache


def get_recipes_cache() -> RecipesCache:
    """Get or create the shared recipes cache."""
    global _recipes_cache
    if _recipes_cache is None:
        _recipes_cache = RecipesCache()
    return _recipes_cache


def get_workforce_cache() -> WorkforceCache:
    """Get or create the shared workforce cache."""
    global _workforce_cache
    if _workforce_cache is None:
        _workforce_cache = WorkforceCache()
    return _workforce_cache


def get_materials_cache() -> MaterialsCache:
    """Get or create the shared materials cache."""
    global _materials_cache
    if _materials_cache is None:
        _materials_cache = MaterialsCache()
    return _materials_cache


async def _ensure_caches_populated() -> None:
    """Ensure all required caches are populated and valid."""
    client = get_fio_client()

    buildings_cache = get_buildings_cache()
    recipes_cache = get_recipes_cache()
    workforce_cache = get_workforce_cache()

    tasks = []

    if not buildings_cache.is_valid():
        tasks.append(("buildings", client.get_all_buildings()))
    if not recipes_cache.is_valid():
        tasks.append(("recipes", client.get_all_recipes()))
    if not workforce_cache.is_valid():
        tasks.append(("workforce", client.get_workforce_needs()))

    if tasks:
        results = await asyncio.gather(*[t[1] for t in tasks])
        for i, (cache_type, _) in enumerate(tasks):
            if cache_type == "buildings":
                buildings_cache.refresh(results[i])
            elif cache_type == "recipes":
                recipes_cache.refresh(results[i])
            elif cache_type == "workforce":
                workforce_cache.refresh(results[i])


@mcp.tool()
async def calculate_permit_io(
    production: list[dict[str, Any]],
    habitation: list[dict[str, Any]],
    exchange: str,
    permits: int = 1,
    extraction: list[dict[str, Any]] | None = None,
    planet: str | None = None,
) -> str | list[TextContent]:
    """Calculate daily material I/O for a base.

    Args:
        production: List of production lines, each with:
                   - recipe: Recipe name (e.g., "1xGRN 1xALG 1xVEG=>10xRAT")
                   - count: Number of buildings running this recipe
                   - efficiency: Efficiency multiplier (e.g., 1.4 for 140%)
        habitation: List of habitation buildings, each with:
                   - building: Building ticker (e.g., "HB1")
                   - count: Number of buildings
        exchange: Exchange code for pricing (e.g., "CI1").
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.
        permits: Number of permits for this base (default: 1).
                 Area limits: 1 permit = 500, 2 = 750, 3 = 1000.
        extraction: List of extraction operations (optional), each with:
                   - building: Extraction building ticker (EXT, RIG, COL)
                   - resource: Material ticker to extract (e.g., "GAL", "FEO")
                   - count: Number of buildings
                   - efficiency: Efficiency multiplier (default: 1.0)
        planet: Planet identifier (required if extraction is provided).
                Used to look up resource factors for extraction calculations.

    Returns:
        TOON-encoded daily I/O breakdown with:
        - materials: List of {ticker, in, out, delta, cis_per_day}
        - workforce: Required workers by type
        - habitation: Capacity vs required validation
        - area: Used vs limit validation
        - totals: Net CIS/day
    """
    # Validate exchange
    exchange = exchange.strip().upper()
    if exchange not in VALID_EXCHANGES:
        valid_list = ", ".join(sorted(VALID_EXCHANGES))
        return [
            TextContent(
                type="text",
                text=f"Invalid exchange: {exchange}. Valid: {valid_list}",
            )
        ]

    # Validate production entries
    if not production:
        return [TextContent(type="text", text="No production entries provided")]

    for i, entry in enumerate(production):
        if "recipe" not in entry:
            return [
                TextContent(type="text", text=f"Production entry {i}: missing 'recipe'")
            ]
        if "count" not in entry:
            return [
                TextContent(type="text", text=f"Production entry {i}: missing 'count'")
            ]
        if "efficiency" not in entry:
            return [
                TextContent(
                    type="text", text=f"Production entry {i}: missing 'efficiency'"
                )
            ]
        if entry["count"] < 1:
            return [
                TextContent(
                    type="text", text=f"Production entry {i}: count must be >= 1"
                )
            ]
        if entry["efficiency"] <= 0:
            return [
                TextContent(
                    type="text", text=f"Production entry {i}: efficiency must be > 0"
                )
            ]

    # Validate habitation entries
    for i, entry in enumerate(habitation):
        if "building" not in entry:
            return [
                TextContent(
                    type="text", text=f"Habitation entry {i}: missing 'building'"
                )
            ]
        if "count" not in entry:
            return [
                TextContent(type="text", text=f"Habitation entry {i}: missing 'count'")
            ]
        building = entry["building"].upper()
        if building not in HABITATION_CAPACITY:
            valid_habs = ", ".join(sorted(HABITATION_CAPACITY.keys()))
            return [
                TextContent(
                    type="text",
                    text=f"Unknown habitation building: {building}. Valid: {valid_habs}",
                )
            ]

    # Validate permits
    if permits < 1:
        return [TextContent(type="text", text="permits must be at least 1")]

    # Validate extraction entries
    if extraction:
        if not planet:
            return [
                TextContent(
                    type="text",
                    text="planet parameter is required when extraction is provided",
                )
            ]

        for i, entry in enumerate(extraction):
            if "building" not in entry:
                return [
                    TextContent(
                        type="text", text=f"Extraction entry {i}: missing 'building'"
                    )
                ]
            building = entry["building"].upper()
            if building not in VALID_EXTRACTION_BUILDINGS:
                valid_list = ", ".join(sorted(VALID_EXTRACTION_BUILDINGS))
                return [
                    TextContent(
                        type="text",
                        text=f"Extraction entry {i}: unknown building '{building}'. "
                        f"Valid: {valid_list}",
                    )
                ]
            if "resource" not in entry:
                return [
                    TextContent(
                        type="text", text=f"Extraction entry {i}: missing 'resource'"
                    )
                ]
            if "count" not in entry:
                return [
                    TextContent(
                        type="text", text=f"Extraction entry {i}: missing 'count'"
                    )
                ]
            if entry["count"] < 1:
                return [
                    TextContent(
                        type="text",
                        text=f"Extraction entry {i}: count must be >= 1",
                    )
                ]
            efficiency = entry.get("efficiency", 1.0)
            if efficiency <= 0:
                return [
                    TextContent(
                        type="text",
                        text=f"Extraction entry {i}: efficiency must be > 0",
                    )
                ]

    try:
        await _ensure_caches_populated()

        recipes_cache = get_recipes_cache()
        buildings_cache = get_buildings_cache()
        workforce_cache = get_workforce_cache()

        # Aggregate material flows: ticker -> {"in": float, "out": float}
        material_flow: dict[str, dict[str, float]] = {}
        # Aggregate workforce: type -> count
        total_workforce: dict[str, int] = {wf: 0 for wf in WORKFORCE_TYPES}
        # Track total area used
        total_area = 0
        # Track errors
        errors: list[str] = []

        # Process each production line
        for entry in production:
            recipe_name = entry["recipe"]
            count = entry["count"]
            efficiency = entry["efficiency"]

            # Look up recipe
            recipe_data = recipes_cache.get_recipe_by_name(recipe_name)
            if not recipe_data:
                errors.append(f"Recipe not found: {recipe_name}")
                continue

            # Get building info
            building_ticker = recipe_data.get("BuildingTicker", "")
            building = buildings_cache.get_building(building_ticker)
            if not building:
                errors.append(f"Building not found: {building_ticker}")
                continue

            # Calculate runs per day
            duration_ms = recipe_data.get("TimeMs") or recipe_data.get("DurationMs", 0)
            if duration_ms <= 0:
                errors.append(f"Invalid recipe duration for {recipe_name}")
                continue

            runs_per_day = MS_PER_DAY / duration_ms * count * efficiency

            # Aggregate inputs
            for inp in recipe_data.get("Inputs", []):
                ticker = inp.get("Ticker", "")
                amount = inp.get("Amount", 0)
                daily_amount = runs_per_day * amount

                if ticker not in material_flow:
                    material_flow[ticker] = {"in": 0, "out": 0}
                material_flow[ticker]["in"] += daily_amount

            # Aggregate outputs
            for out in recipe_data.get("Outputs", []):
                ticker = out.get("Ticker", "")
                amount = out.get("Amount", 0)
                daily_amount = runs_per_day * amount

                if ticker not in material_flow:
                    material_flow[ticker] = {"in": 0, "out": 0}
                material_flow[ticker]["out"] += daily_amount

            # Aggregate workforce
            for wf_type in WORKFORCE_TYPES:
                worker_count = building.get(wf_type, 0) * count
                total_workforce[wf_type] += worker_count

            # Track area used by production buildings
            area_cost = building.get("AreaCost", 0)
            total_area += area_cost * count

        # Process extraction entries
        extraction_errors: list[str] = []
        if extraction and planet:
            # Fetch planet data to get resource factors
            client = get_fio_client()
            materials_cache = get_materials_cache()

            # Ensure materials cache is populated for MaterialId -> Ticker lookup
            if not materials_cache.is_valid():
                materials = await client.get_all_materials()
                materials_cache.refresh(materials)

            try:
                planet_data = await client.get_planet(planet)

                # Build ticker -> {type, factor} mapping from planet resources
                planet_resources: dict[str, dict[str, Any]] = {}
                for resource in planet_data.get("Resources", []):
                    mat_id = resource.get("MaterialId", "")
                    # Look up ticker from materials cache
                    mat_info = materials_cache.get_material(mat_id)
                    if mat_info:
                        ticker = mat_info.get("Ticker", "")
                        if ticker:
                            planet_resources[ticker.upper()] = {
                                "type": resource.get("ResourceType", ""),
                                "factor": resource.get("Factor", 0.0),
                            }

                # Process each extraction entry
                for entry in extraction:
                    building_ticker = entry["building"].upper()
                    resource_ticker = entry["resource"].upper()
                    count = entry["count"]
                    efficiency = entry.get("efficiency", 1.0)

                    # Look up resource on planet
                    if resource_ticker not in planet_resources:
                        extraction_errors.append(
                            f"Resource {resource_ticker} not found on planet {planet}"
                        )
                        continue

                    resource_info = planet_resources[resource_ticker]
                    resource_type = resource_info["type"]
                    factor = resource_info["factor"]

                    # Validate building matches resource type
                    expected_building = get_building_for_resource_type(resource_type)
                    if expected_building != building_ticker:
                        extraction_errors.append(
                            f"Building {building_ticker} cannot extract "
                            f"{resource_type} resources (use {expected_building})"
                        )
                        continue

                    # Calculate daily output using PCT formula
                    daily_output = calculate_extraction_output(
                        factor=factor,
                        efficiency=efficiency,
                        count=count,
                        resource_type=resource_type,
                    )

                    # Add to material flow as output
                    if resource_ticker not in material_flow:
                        material_flow[resource_ticker] = {"in": 0, "out": 0}
                    material_flow[resource_ticker]["out"] += daily_output

                    # Add workforce requirements from extraction building
                    building_spec = EXTRACTION_BUILDINGS[building_ticker]
                    for wf_type, worker_count in building_spec["workforce"].items():
                        total_workforce[wf_type] += worker_count * count

                    # Add area cost
                    total_area += building_spec["area"] * count

            except FIONotFoundError:
                extraction_errors.append(f"Planet not found: {planet}")

        # Add habitation building areas
        for entry in habitation:
            hab_ticker = entry["building"].upper()
            hab_building = buildings_cache.get_building(hab_ticker)
            if hab_building:
                area_cost = hab_building.get("AreaCost", 0)
                total_area += area_cost * entry["count"]

        # Calculate workforce consumables
        for wf_type, worker_count in total_workforce.items():
            if worker_count <= 0:
                continue

            wf_type_upper = wf_type.upper()
            if wf_type_upper.endswith("S"):
                wf_type_upper = wf_type_upper[:-1]

            needs = workforce_cache.get_needs(wf_type_upper)
            if not needs:
                continue

            for need in needs:
                ticker = need.get("MaterialTicker", "")
                # Amount is per 100 workers per day
                amount_per_100 = need.get("Amount", 0)
                daily_amount = (worker_count / 100) * amount_per_100

                if ticker not in material_flow:
                    material_flow[ticker] = {"in": 0, "out": 0}
                material_flow[ticker]["in"] += daily_amount

        # Calculate habitation capacity
        hab_capacity: dict[str, int] = {wf: 0 for wf in WORKFORCE_TYPES}
        for entry in habitation:
            building = entry["building"].upper()
            count = entry["count"]
            capacity = HABITATION_CAPACITY.get(building, {})
            for wf_type, cap in capacity.items():
                hab_capacity[wf_type] += cap * count

        # Validate habitation
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

        # Fetch all prices
        all_tickers = list(material_flow.keys())
        prices = await fetch_prices(all_tickers, exchange)

        # Build output table
        materials_output: list[dict[str, Any]] = []
        total_cis_per_day = 0.0
        missing_prices: list[str] = []

        for ticker in sorted(material_flow.keys()):
            flow = material_flow[ticker]
            in_amount = flow["in"]
            out_amount = flow["out"]
            delta = out_amount - in_amount

            price_data = prices.get(ticker, {"ask": None, "bid": None})
            ask = price_data.get("ask")
            bid = price_data.get("bid")

            # Calculate CIS/day: sell surplus at Bid, buy deficit at Ask
            cis_per_day: float | None = None
            if delta > 0 and bid is not None:
                cis_per_day = delta * bid
                total_cis_per_day += cis_per_day
            elif delta < 0 and ask is not None:
                cis_per_day = delta * ask  # negative * positive = negative
                total_cis_per_day += cis_per_day
            elif delta == 0:
                cis_per_day = 0
            else:
                missing_prices.append(ticker)

            materials_output.append(
                {
                    "ticker": ticker,
                    "in": round(in_amount, 2),
                    "out": round(out_amount, 2),
                    "delta": round(delta, 2),
                    "cis_per_day": round(cis_per_day, 2)
                    if cis_per_day is not None
                    else None,
                }
            )

        # Calculate area limit
        area_limit = calculate_area_limit(permits)

        # Build result
        result: dict[str, Any] = {
            "exchange": exchange,
            "materials": materials_output,
            "workforce": {
                wf: count for wf, count in total_workforce.items() if count > 0
            },
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

        return toon_encode(prettify_names(result))

    except FIOApiError as e:
        logger.exception("FIO API error while calculating base I/O")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
