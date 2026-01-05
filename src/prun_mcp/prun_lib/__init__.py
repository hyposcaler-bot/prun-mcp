"""Prosperous Universe business logic library.

This module provides reusable game logic functions that are independent
of the MCP presentation layer. Functions here accept and return typed
Pydantic models.
"""

# Main entry point functions
from prun_mcp.prun_lib.base import calculate_area_limit
from prun_mcp.prun_lib.base_io import calculate_base_io
from prun_mcp.prun_lib.building import (
    BuildingCostError,
    InfertilePlanetError,
    calculate_building_cost,
    calculate_building_cost_async,
)
from prun_mcp.prun_lib.cogm import (
    COGMCalculationError,
    InvalidRecipeError,
    calculate_cogm,
)

# Unified exception classes
from prun_mcp.prun_lib.exceptions import (
    BuildingNotFoundError,
    MaterialNotFoundError,
    PlanetNotFoundError,
    RecipeNotFoundError,
)

# Exchange validation
from prun_mcp.prun_lib.exchange import (
    VALID_EXCHANGES,
    InvalidExchangeError,
    validate_exchange,
)

__all__ = [
    # Entry points
    "calculate_area_limit",
    "calculate_base_io",
    "calculate_building_cost",
    "calculate_building_cost_async",
    "calculate_cogm",
    # Unified exceptions
    "BuildingNotFoundError",
    "MaterialNotFoundError",
    "PlanetNotFoundError",
    "RecipeNotFoundError",
    # Module-specific exceptions
    "BuildingCostError",
    "COGMCalculationError",
    "InfertilePlanetError",
    "InvalidRecipeError",
    "InvalidExchangeError",
    # Exchange
    "VALID_EXCHANGES",
    "validate_exchange",
]
