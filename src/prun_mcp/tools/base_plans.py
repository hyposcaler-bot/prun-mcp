"""Base plan management MCP tools."""

import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.storage import BasePlanStorage
from prun_mcp.tools.permit_io import calculate_permit_io
from prun_mcp.utils import prettify_names

logger = logging.getLogger(__name__)

# Shared storage instance (singleton pattern)
_base_plan_storage: BasePlanStorage | None = None


def get_base_plan_storage() -> BasePlanStorage:
    """Get or create the shared base plan storage."""
    global _base_plan_storage
    if _base_plan_storage is None:
        _base_plan_storage = BasePlanStorage()
    return _base_plan_storage


@mcp.tool()
async def save_base_plan(
    name: str,
    planet: str,
    habitation: list[dict[str, Any]],
    production: list[dict[str, Any]],
    planet_name: str | None = None,
    cogc_program: str | None = None,
    expertise: dict[str, int] | None = None,
    storage: list[dict[str, Any]] | None = None,
    extraction: list[dict[str, Any]] | None = None,
    notes: str | None = None,
    overwrite: bool = False,
) -> str | list[TextContent]:
    """Creates or updates a base plan.

    Args:
        name: Plan identifier (unique name).
        planet: Planet ID (e.g., "KW-020c").
        habitation: Habitation buildings, each with:
                   - building: Building ticker (e.g., "HB1")
                   - count: Number of buildings
        production: Recipe assignments, each with:
                   - recipe: Full recipe name (e.g., "1xGRN 1xALG 1xVEG=>10xRAT")
                   - count: Number of buildings running this recipe
                   - efficiency: Efficiency multiplier (e.g., 1.33 for 133%)
        planet_name: Human-readable planet name (optional).
        cogc_program: Active COGC program if any (optional).
        expertise: Expert counts by category using PascalCase keys (optional).
                  Valid keys: Agriculture, Chemistry, Construction, Electronics,
                  FoodIndustries, FuelRefining, Manufacturing, Metallurgy,
                  ResourceExtraction.
        storage: Storage buildings with capacity (optional), each with:
                - building: Storage ticker (e.g., "STO")
                - count: Number of buildings
                - capacity: Storage capacity
        extraction: Resource extraction operations (optional), each with:
                   - building: Extraction building ticker (EXT, RIG, COL)
                   - resource: Material ticker to extract (e.g., "GAL", "FEO")
                   - count: Number of buildings
                   - efficiency: Efficiency multiplier (default: 1.0)
        notes: Freeform notes (optional).
        overwrite: Must be true to update an existing plan.

    Returns:
        TOON-encoded saved plan with any validation warnings.
    """
    # Build plan dictionary
    plan: dict[str, Any] = {
        "name": name,
        "planet": planet,
        "habitation": habitation,
        "production": production,
    }

    if planet_name:
        plan["planet_name"] = planet_name
    if cogc_program:
        plan["cogc_program"] = cogc_program
    if expertise:
        plan["expertise"] = expertise
    if storage:
        plan["storage"] = storage
    if extraction:
        plan["extraction"] = extraction
    if notes:
        plan["notes"] = notes

    # Save to storage
    storage_instance = get_base_plan_storage()
    try:
        saved_plan, warnings = storage_instance.save_plan(plan, overwrite=overwrite)
    except ValueError as e:
        return [TextContent(type="text", text=str(e))]

    # Build response
    result: dict[str, Any] = {"plan": saved_plan}
    if warnings:
        result["warnings"] = warnings

    return toon_encode(prettify_names(result))


@mcp.tool()
async def get_base_plan(name: str) -> str | list[TextContent]:
    """Retrieves a single base plan by name.

    Args:
        name: Plan identifier.

    Returns:
        TOON-encoded plan data or error if not found.
    """
    storage_instance = get_base_plan_storage()
    plan = storage_instance.get_plan(name)

    if plan is None:
        return [TextContent(type="text", text=f"Plan not found: {name}")]

    return toon_encode(prettify_names(plan))


@mcp.tool()
async def list_base_plans() -> str:
    """Lists all stored base plans.

    Returns:
        TOON-encoded array of plan summaries containing:
        - name: Plan identifier
        - planet: Planet ID
        - planet_name: Human-readable name (if set)
        - updated_at: Last update timestamp
    """
    storage_instance = get_base_plan_storage()
    plans = storage_instance.list_plans()

    return toon_encode({"plans": plans})


@mcp.tool()
async def delete_base_plan(name: str) -> str | list[TextContent]:
    """Removes a base plan.

    Args:
        name: Plan identifier.

    Returns:
        Success confirmation or error if not found.
    """
    storage_instance = get_base_plan_storage()
    deleted = storage_instance.delete_plan(name)

    if not deleted:
        return [TextContent(type="text", text=f"Plan not found: {name}")]

    return toon_encode({"deleted": name, "success": True})


@mcp.tool()
async def calculate_plan_io(
    name: str,
    exchange: str,
) -> str | list[TextContent]:
    """Calculates daily I/O for a saved base plan.

    Loads the specified plan and calculates material input/output,
    workforce requirements, and daily costs using current market prices.

    Args:
        name: Plan identifier.
        exchange: Exchange code for pricing (e.g., "CI1").
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.

    Returns:
        TOON-encoded I/O breakdown (same format as calculate_permit_io):
        - materials: List of {ticker, in, out, delta, cis_per_day}
        - workforce: Required workers by type
        - habitation: Capacity vs required validation
        - area: Used vs limit validation
        - totals: Net CIS/day
    """
    storage_instance = get_base_plan_storage()
    plan = storage_instance.get_plan(name)

    if plan is None:
        return [TextContent(type="text", text=f"Plan not found: {name}")]

    # Transform plan data to calculate_permit_io format
    production = [
        {
            "recipe": p["recipe"],
            "count": p["count"],
            "efficiency": p.get("efficiency", 1.0),
        }
        for p in plan.get("production", [])
    ]

    habitation = [
        {"building": h["building"], "count": h["count"]}
        for h in plan.get("habitation", [])
    ]

    # Extract extraction data if present
    extraction = None
    if plan.get("extraction"):
        extraction = [
            {
                "building": e["building"],
                "resource": e["resource"],
                "count": e["count"],
                "efficiency": e.get("efficiency", 1.0),
            }
            for e in plan["extraction"]
        ]

    # Call calculate_permit_io with extracted data
    return await calculate_permit_io(
        production=production,
        habitation=habitation,
        exchange=exchange,
        permits=1,  # Could be added to plan schema in future
        extraction=extraction,
        planet=plan.get("planet") if extraction else None,
    )
