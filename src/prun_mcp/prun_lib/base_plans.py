"""Base plans business logic."""

from typing import Any

from prun_mcp.prun_lib.base_io import calculate_base_io
from prun_mcp.storage import BasePlanStorage
from prun_mcp.utils import prettify_names


class BasePlansError(Exception):
    """Base error for base plans operations."""

    pass


class PlanNotFoundError(BasePlansError):
    """Plan not found in storage."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Plan not found: {name}")


class PlanSaveError(BasePlansError):
    """Error saving plan."""

    pass


# Shared storage instance (singleton pattern)
_base_plan_storage: Any = None


def get_base_plan_storage() -> BasePlanStorage:
    """Get or create the shared base plan storage."""
    global _base_plan_storage
    if _base_plan_storage is None:
        _base_plan_storage = BasePlanStorage()
    return _base_plan_storage


async def save_base_plan_async(
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
) -> dict[str, Any]:
    """Creates or updates a base plan.

    Args:
        name: Plan identifier (unique name).
        planet: Planet ID (e.g., "KW-020c").
        habitation: Habitation buildings with building and count.
        production: Recipe assignments with recipe, count, efficiency.
        planet_name: Human-readable planet name (optional).
        cogc_program: Active COGC program if any (optional).
        expertise: Expert counts by category (optional).
        storage: Storage buildings with capacity (optional).
        extraction: Resource extraction operations (optional).
        notes: Freeform notes (optional).
        active: Whether the plan represents an active in-game base.
        overwrite: Must be true to update an existing plan.

    Returns:
        Dict with 'plan' and optional 'warnings'.

    Raises:
        PlanSaveError: If plan cannot be saved.
    """
    # Build plan dictionary
    plan: dict[str, Any] = {
        "name": name,
        "planet": planet,
        "habitation": habitation,
        "production": production,
        "active": active,
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
        raise PlanSaveError(str(e))

    # Build response
    result: dict[str, Any] = {"plan": saved_plan}
    if warnings:
        result["warnings"] = warnings

    return prettify_names(result)


async def get_base_plan_async(name: str) -> dict[str, Any]:
    """Retrieves a single base plan by name.

    Args:
        name: Plan identifier.

    Returns:
        Plan data.

    Raises:
        PlanNotFoundError: If plan is not found.
    """
    storage_instance = get_base_plan_storage()
    plan = storage_instance.get_plan(name)

    if plan is None:
        raise PlanNotFoundError(name)

    return prettify_names(plan)


async def list_base_plans_async(active: bool | None = None) -> dict[str, Any]:
    """Lists all stored base plans.

    Args:
        active: Filter by active status (optional).

    Returns:
        Dict with 'plans' list containing plan summaries.
    """
    storage_instance = get_base_plan_storage()
    plans = storage_instance.list_plans(active=active)

    return {"plans": plans}


async def delete_base_plan_async(name: str) -> dict[str, Any]:
    """Removes a base plan.

    Args:
        name: Plan identifier.

    Returns:
        Dict with 'deleted' name and 'success' status.

    Raises:
        PlanNotFoundError: If plan is not found.
    """
    storage_instance = get_base_plan_storage()
    deleted = storage_instance.delete_plan(name)

    if not deleted:
        raise PlanNotFoundError(name)

    return {"deleted": name, "success": True}


async def calculate_plan_io_async(
    name: str,
    exchange: str,
) -> Any:
    """Calculates daily I/O for a saved base plan.

    Args:
        name: Plan identifier.
        exchange: Exchange code for pricing.

    Returns:
        I/O calculation result (same as calculate_base_io).

    Raises:
        PlanNotFoundError: If plan is not found.
    """
    storage_instance = get_base_plan_storage()
    plan = storage_instance.get_plan(name)

    if plan is None:
        raise PlanNotFoundError(name)

    # Transform plan data to calculate_base_io format
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

    # Call calculate_base_io with extracted data
    return await calculate_base_io(
        production=production,
        habitation=habitation,
        exchange=exchange,
        permits=1,  # Could be added to plan schema in future
        extraction=extraction,
        planet=plan.get("planet") if extraction else None,
    )
