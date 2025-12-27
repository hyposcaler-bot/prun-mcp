"""Permit daily I/O calculator tool."""

import asyncio
import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import BuildingsCache, RecipesCache, WorkforceCache
from prun_mcp.fio import FIOApiError, get_fio_client
from prun_mcp.resources.exchanges import VALID_EXCHANGES
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
                  See exchange://list resource for code-to-name mapping.
        permits: Number of permits for this base (default: 1).
                 Area limits: 1 permit = 500, 2 = 750, 3 = 1000.

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
        if missing_prices:
            result["missing_prices"] = missing_prices

        return toon_encode(prettify_names(result))

    except FIOApiError as e:
        logger.exception("FIO API error while calculating base I/O")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
