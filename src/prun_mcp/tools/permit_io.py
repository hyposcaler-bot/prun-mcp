"""Permit daily I/O calculator tool."""

import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import (
    ensure_buildings_cache,
    ensure_materials_cache,
    ensure_recipes_cache,
    ensure_workforce_cache,
)
from prun_mcp.fio import FIOApiError, FIONotFoundError, get_fio_client
from prun_mcp.prun_lib import InvalidExchangeError, validate_exchange
from prun_mcp.resources.extraction import (
    EXTRACTION_BUILDINGS,
    VALID_EXTRACTION_BUILDINGS,
    calculate_extraction_output,
    get_building_for_resource_type,
)
from prun_mcp.resources.workforce import HABITATION_CAPACITY, WORKFORCE_TYPES
from prun_mcp.utils import fetch_prices

logger = logging.getLogger(__name__)

MS_PER_DAY = 24 * 60 * 60 * 1000


def calculate_area_limit(permits: int) -> int:
    """Calculate area limit for given number of permits."""
    if permits <= 0:
        return 0
    return 500 + max(0, permits - 1) * 250


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
        production: List of production lines with recipe, count, efficiency.
        habitation: List of habitation buildings with building, count.
        exchange: Exchange code for pricing. Valid: AI1, CI1, CI2, IC1, NC1, NC2.
        permits: Number of permits for this base (default: 1).
        extraction: Optional extraction operations with building, resource, count.
        planet: Planet identifier (required if extraction is provided).

    Returns:
        TOON-encoded daily I/O breakdown with materials, workforce, area.
    """
    try:
        validated_exchange = validate_exchange(exchange)
    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]

    if validated_exchange is None:
        return [TextContent(type="text", text="Exchange is required")]
    exchange = validated_exchange

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
                        text=f"Extraction entry {i}: unknown building '{building}'. Valid: {valid_list}",
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
                        type="text", text=f"Extraction entry {i}: count must be >= 1"
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
        recipes_cache = await ensure_recipes_cache()
        buildings_cache = await ensure_buildings_cache()
        workforce_cache = await ensure_workforce_cache()

        material_flow: dict[str, dict[str, float]] = {}
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

            duration_ms = recipe_data.get("TimeMs") or recipe_data.get("DurationMs", 0)
            if duration_ms <= 0:
                errors.append(f"Invalid recipe duration for {recipe_name}")
                continue

            runs_per_day = MS_PER_DAY / duration_ms * count * efficiency

            for inp in recipe_data.get("Inputs", []):
                ticker = inp.get("Ticker", "")
                amount = inp.get("Amount", 0)
                daily_amount = runs_per_day * amount
                if ticker not in material_flow:
                    material_flow[ticker] = {"in": 0, "out": 0}
                material_flow[ticker]["in"] += daily_amount

            for out in recipe_data.get("Outputs", []):
                ticker = out.get("Ticker", "")
                amount = out.get("Amount", 0)
                daily_amount = runs_per_day * amount
                if ticker not in material_flow:
                    material_flow[ticker] = {"in": 0, "out": 0}
                material_flow[ticker]["out"] += daily_amount

            for wf_type in WORKFORCE_TYPES:
                worker_count = building.get(wf_type, 0) * count
                total_workforce[wf_type] += worker_count

            area_cost = building.get("AreaCost", 0)
            total_area += area_cost * count

        # Process extraction
        extraction_errors: list[str] = []
        if extraction and planet:
            client = get_fio_client()
            materials_cache = await ensure_materials_cache()

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
                            f"Building {building_ticker} cannot extract {resource_type} resources (use {expected_building})"
                        )
                        continue

                    daily_output = calculate_extraction_output(
                        factor=factor,
                        efficiency=efficiency,
                        count=count,
                        resource_type=resource_type,
                    )

                    if resource_ticker not in material_flow:
                        material_flow[resource_ticker] = {"in": 0, "out": 0}
                    material_flow[resource_ticker]["out"] += daily_output

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
        all_tickers = list(material_flow.keys())
        prices = await fetch_prices(all_tickers, exchange)

        # Build output
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

            cis_per_day: float | None = None
            if delta > 0 and bid is not None:
                cis_per_day = delta * bid
                total_cis_per_day += cis_per_day
            elif delta < 0 and ask is not None:
                cis_per_day = delta * ask
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

        area_limit = calculate_area_limit(permits)

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

        return toon_encode(result)

    except FIOApiError as e:
        logger.exception("FIO API error while calculating base I/O")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
