"""Base plan management MCP tools."""

import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError
from prun_mcp.prun_lib.base_plans import (
    PlanNotFoundError,
    PlanSaveError,
    calculate_plan_io_async,
    delete_base_plan_async,
    get_base_plan_async,
    list_base_plans_async,
    save_base_plan_async,
)

logger = logging.getLogger(__name__)


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
    active: bool = False,
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
        active: Whether the plan represents an active in-game base (default: False).
                Active plans represent real bases/permits; inactive plans are for
                planning or reference only.
        overwrite: Must be true to update an existing plan.

    Returns:
        TOON-encoded saved plan with any validation warnings.
    """
    try:
        result = await save_base_plan_async(
            name=name,
            planet=planet,
            habitation=habitation,
            production=production,
            planet_name=planet_name,
            cogc_program=cogc_program,
            expertise=expertise,
            storage=storage,
            extraction=extraction,
            notes=notes,
            active=active,
            overwrite=overwrite,
        )
        return toon_encode(result)
    except PlanSaveError as e:
        return [TextContent(type="text", text=str(e))]


@mcp.tool()
async def get_base_plan(name: str) -> str | list[TextContent]:
    """Retrieves a single base plan by name.

    Args:
        name: Plan identifier.

    Returns:
        TOON-encoded plan data or error if not found.
    """
    try:
        result = await get_base_plan_async(name)
        return toon_encode(result)
    except PlanNotFoundError as e:
        return [TextContent(type="text", text=str(e))]


@mcp.tool()
async def list_base_plans(active: bool | None = None) -> str:
    """Lists all stored base plans.

    Args:
        active: Filter by active status (optional).
                If None, returns all plans.
                If True, returns only active plans (real in-game bases).
                If False, returns only inactive plans (planning/reference).

    Returns:
        TOON-encoded array of plan summaries containing:
        - name: Plan identifier
        - planet: Planet ID
        - planet_name: Human-readable name (if set)
        - active: Whether the plan is active
        - updated_at: Last update timestamp
    """
    result = await list_base_plans_async(active=active)
    return toon_encode(result)


@mcp.tool()
async def delete_base_plan(name: str) -> str | list[TextContent]:
    """Removes a base plan.

    Args:
        name: Plan identifier.

    Returns:
        Success confirmation or error if not found.
    """
    try:
        result = await delete_base_plan_async(name)
        return toon_encode(result)
    except PlanNotFoundError as e:
        return [TextContent(type="text", text=str(e))]


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
    try:
        result = await calculate_plan_io_async(name=name, exchange=exchange)
        return toon_encode(result)
    except PlanNotFoundError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while calculating plan I/O")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
