"""Prosperous Universe business logic library.

This module provides reusable game logic functions that are independent
of the MCP presentation layer. Functions here accept and return typed
Pydantic models.
"""

from prun_mcp.prun_lib.building import (
    BuildingCostError,
    InfertilePlanetError,
    calculate_building_cost,
    get_required_infrastructure_materials,
)
from prun_mcp.prun_lib.exchange import (
    EXCHANGES,
    VALID_EXCHANGES,
    InvalidExchangeError,
    format_exchange_list,
    validate_exchange,
)

__all__ = [
    # Building
    "BuildingCostError",
    "InfertilePlanetError",
    "calculate_building_cost",
    "get_required_infrastructure_materials",
    # Exchange
    "EXCHANGES",
    "VALID_EXCHANGES",
    "InvalidExchangeError",
    "format_exchange_list",
    "validate_exchange",
]
