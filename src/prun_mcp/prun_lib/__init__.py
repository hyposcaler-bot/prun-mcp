"""Prosperous Universe business logic library.

This module provides reusable game logic functions that are independent
of the MCP presentation layer. Functions here accept and return typed
Pydantic models.
"""

from prun_mcp.prun_lib.base import calculate_area_limit
from prun_mcp.prun_lib.base_io import calculate_base_io
from prun_mcp.prun_lib.building import (
    BuildingCostError,
    BuildingNotFoundError as BuildingCostBuildingNotFoundError,
    InfertilePlanetError,
    PlanetNotFoundError,
    calculate_building_cost,
    calculate_building_cost_async,
    get_required_infrastructure_materials,
)
from prun_mcp.prun_lib.cogm import (
    BuildingNotFoundError,
    COGMCalculationError,
    InvalidRecipeError,
    RecipeNotFoundError,
    calculate_cogm,
    calculate_consumable_costs,
    calculate_input_costs,
    calculate_runs_per_day,
)
from prun_mcp.prun_lib.exchange import (
    EXCHANGES,
    VALID_EXCHANGES,
    InvalidExchangeError,
    format_exchange_list,
    validate_exchange,
)
from prun_mcp.prun_lib.market import (
    SPREAD_WARNING_THRESHOLD,
    SUPPLY_DEMAND_IMBALANCE,
    THIN_DEPTH_THRESHOLD,
    aggregate_orders_by_price,
    build_order_book_levels,
    calculate_price_stats,
    format_number,
    generate_fill_recommendations,
    generate_history_insights,
    generate_market_warnings,
    walk_order_book,
)
from prun_mcp.prun_lib.material_flow import (
    MaterialFlowTracker,
    calculate_material_values,
    calculate_production_runs_per_day,
    process_recipe_flow,
)
from prun_mcp.prun_lib.workforce import (
    WORKFORCE_TYPES,
    WorkforceNeedsProvider,
    aggregate_workforce,
    calculate_workforce_consumption,
    get_consumable_tickers,
    get_workforce_from_building,
    normalize_workforce_type,
)

__all__ = [
    # Base
    "calculate_area_limit",
    # Base I/O
    "calculate_base_io",
    # Building
    "BuildingCostError",
    "BuildingCostBuildingNotFoundError",
    "InfertilePlanetError",
    "PlanetNotFoundError",
    "calculate_building_cost",
    "calculate_building_cost_async",
    "get_required_infrastructure_materials",
    # COGM
    "BuildingNotFoundError",
    "COGMCalculationError",
    "InvalidRecipeError",
    "RecipeNotFoundError",
    "calculate_cogm",
    "calculate_consumable_costs",
    "calculate_input_costs",
    "calculate_runs_per_day",
    # Exchange
    "EXCHANGES",
    "VALID_EXCHANGES",
    "InvalidExchangeError",
    "format_exchange_list",
    "validate_exchange",
    # Market
    "SPREAD_WARNING_THRESHOLD",
    "SUPPLY_DEMAND_IMBALANCE",
    "THIN_DEPTH_THRESHOLD",
    "aggregate_orders_by_price",
    "build_order_book_levels",
    "calculate_price_stats",
    "format_number",
    "generate_fill_recommendations",
    "generate_history_insights",
    "generate_market_warnings",
    "walk_order_book",
    # Material Flow
    "MaterialFlowTracker",
    "calculate_material_values",
    "calculate_production_runs_per_day",
    "process_recipe_flow",
    # Workforce
    "WORKFORCE_TYPES",
    "WorkforceNeedsProvider",
    "aggregate_workforce",
    "calculate_workforce_consumption",
    "get_consumable_tickers",
    "get_workforce_from_building",
    "normalize_workforce_type",
]
