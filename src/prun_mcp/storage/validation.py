"""Validation constants and functions for base plan storage."""

from typing import Any

from prun_mcp.resources.workforce import VALID_HABITATION

# Valid expertise categories (PascalCase, matching game conventions)
VALID_EXPERTISE = {
    "Agriculture",
    "Chemistry",
    "Construction",
    "Electronics",
    "FoodIndustries",
    "FuelRefining",
    "Manufacturing",
    "Metallurgy",
    "ResourceExtraction",
}

# Valid storage building types
VALID_STORAGE_BUILDINGS = {"STO"}

# Maximum expertise level per category
MAX_EXPERTISE_LEVEL = 5


def validate_base_plan(plan: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Validate a base plan and return errors and warnings.

    Uses lenient validation: warns on unknown values but allows save.

    Args:
        plan: Base plan dictionary to validate.

    Returns:
        Tuple of (errors, warnings) where:
        - errors: List of validation errors that should prevent saving
        - warnings: List of validation warnings (save allowed)
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Required fields
    name = plan.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        errors.append("name must be a non-empty string")

    planet = plan.get("planet")
    if not planet or not isinstance(planet, str) or not planet.strip():
        errors.append("planet must be a non-empty string")

    # Habitation validation
    habitation = plan.get("habitation")
    if habitation is None:
        errors.append("habitation is required")
    elif not isinstance(habitation, list):
        errors.append("habitation must be a list")
    else:
        for i, hab in enumerate(habitation):
            if not isinstance(hab, dict):
                errors.append(f"habitation[{i}] must be an object")
                continue

            building = hab.get("building")
            if not building:
                errors.append(f"habitation[{i}].building is required")
            elif building not in VALID_HABITATION:
                warnings.append(
                    f"habitation[{i}].building '{building}' is not a known "
                    f"habitation type (valid: {', '.join(sorted(VALID_HABITATION))})"
                )

            count = hab.get("count")
            if count is None:
                errors.append(f"habitation[{i}].count is required")
            elif not isinstance(count, int) or count < 0:
                errors.append(f"habitation[{i}].count must be a non-negative integer")

    # Production validation
    production = plan.get("production")
    if production is None:
        errors.append("production is required")
    elif not isinstance(production, list):
        errors.append("production must be a list")
    else:
        for i, prod in enumerate(production):
            if not isinstance(prod, dict):
                errors.append(f"production[{i}] must be an object")
                continue

            recipe = prod.get("recipe")
            if not recipe or not isinstance(recipe, str):
                errors.append(f"production[{i}].recipe is required")
            elif "=>" not in recipe:
                warnings.append(
                    f"production[{i}].recipe '{recipe}' may not be a valid "
                    "recipe format (expected format: '1xINPUT=>1xOUTPUT')"
                )

            count = prod.get("count")
            if count is None:
                errors.append(f"production[{i}].count is required")
            elif not isinstance(count, int) or count < 1:
                errors.append(f"production[{i}].count must be a positive integer")

            efficiency = prod.get("efficiency")
            if efficiency is None:
                errors.append(f"production[{i}].efficiency is required")
            elif not isinstance(efficiency, (int, float)) or efficiency <= 0:
                errors.append(f"production[{i}].efficiency must be a positive number")

    # Optional: Storage validation
    storage = plan.get("storage")
    if storage is not None:
        if not isinstance(storage, list):
            errors.append("storage must be a list")
        else:
            for i, sto in enumerate(storage):
                if not isinstance(sto, dict):
                    errors.append(f"storage[{i}] must be an object")
                    continue

                building = sto.get("building")
                if building and building not in VALID_STORAGE_BUILDINGS:
                    warnings.append(
                        f"storage[{i}].building '{building}' is not a known "
                        f"storage type (valid: {', '.join(sorted(VALID_STORAGE_BUILDINGS))})"
                    )

                count = sto.get("count")
                if count is not None and (not isinstance(count, int) or count < 0):
                    errors.append(f"storage[{i}].count must be a non-negative integer")

                capacity = sto.get("capacity")
                if capacity is not None and (
                    not isinstance(capacity, int) or capacity < 1
                ):
                    errors.append(f"storage[{i}].capacity must be a positive integer")

    # Optional: Expertise validation
    expertise = plan.get("expertise")
    if expertise is not None:
        if not isinstance(expertise, dict):
            errors.append("expertise must be an object")
        else:
            for key, value in expertise.items():
                if key not in VALID_EXPERTISE:
                    warnings.append(
                        f"expertise key '{key}' is not a known category "
                        f"(valid: {', '.join(sorted(VALID_EXPERTISE))})"
                    )

                if not isinstance(value, int) or value < 0:
                    errors.append(f"expertise['{key}'] must be a non-negative integer")
                elif value > MAX_EXPERTISE_LEVEL:
                    warnings.append(
                        f"expertise['{key}'] value {value} exceeds maximum "
                        f"({MAX_EXPERTISE_LEVEL})"
                    )

    return errors, warnings
