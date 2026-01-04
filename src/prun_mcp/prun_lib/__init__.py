"""Prosperous Universe business logic library.

This module provides reusable game logic functions that are independent
of the MCP presentation layer. Functions here accept and return typed
Pydantic models.
"""

from prun_mcp.prun_lib.building import calculate_building_cost

__all__ = ["calculate_building_cost"]
