"""Extraction building constants and utilities.

Provides constants for resource extraction buildings (EXT, RIG, COL) and
calculation utilities using the PCT extraction formula.
"""

from typing import Any

# Extraction building specifications
# Data from FIO API and PCT (pct.fnar.net)
EXTRACTION_BUILDINGS: dict[str, dict[str, Any]] = {
    "EXT": {
        "name": "Extractor",
        "resource_type": "MINERAL",
        "base_multiplier": 0.7,
        "workforce": {"Pioneers": 60},
        "area": 25,
        "expertise": "RESOURCE_EXTRACTION",
    },
    "RIG": {
        "name": "Rig",
        "resource_type": "GASEOUS",
        "base_multiplier": 0.7,
        "workforce": {"Pioneers": 30},
        "area": 10,
        "expertise": "RESOURCE_EXTRACTION",
    },
    "COL": {
        "name": "Collector",
        "resource_type": "LIQUID",
        "base_multiplier": 0.6,
        "workforce": {"Pioneers": 50},
        "area": 15,
        "expertise": "RESOURCE_EXTRACTION",
    },
}

# Map FIO resource types to extraction building tickers
RESOURCE_TYPE_TO_BUILDING: dict[str, str] = {
    "MINERAL": "EXT",
    "GASEOUS": "RIG",
    "ATMOSPHERIC": "RIG",  # FIO uses ATMOSPHERIC for gases
    "LIQUID": "COL",
}

# Valid extraction building tickers
VALID_EXTRACTION_BUILDINGS: set[str] = set(EXTRACTION_BUILDINGS.keys())


def get_building_for_resource_type(resource_type: str) -> str | None:
    """Get the appropriate extraction building for a resource type.

    Args:
        resource_type: FIO resource type (MINERAL, GASEOUS, ATMOSPHERIC, LIQUID)

    Returns:
        Building ticker (EXT, RIG, COL) or None if unknown type.
    """
    return RESOURCE_TYPE_TO_BUILDING.get(resource_type.upper())


def calculate_extraction_output(
    factor: float,
    efficiency: float,
    count: int,
    resource_type: str,
) -> float:
    """Calculate daily extraction output using PCT formula.

    Formula: daily = (factor * 100) * base_multiplier * efficiency * count

    Args:
        factor: Planet resource factor (typically 0.0-1.0)
        efficiency: Efficiency multiplier (e.g., 1.4 for 140%)
        count: Number of extraction buildings
        resource_type: FIO resource type (MINERAL, GASEOUS/ATMOSPHERIC, LIQUID)

    Returns:
        Daily output in units. Returns 0.0 if resource type is unknown.
    """
    building_ticker = RESOURCE_TYPE_TO_BUILDING.get(resource_type.upper())
    if not building_ticker:
        return 0.0

    building = EXTRACTION_BUILDINGS[building_ticker]
    base_multiplier = building["base_multiplier"]

    return (factor * 100) * base_multiplier * efficiency * count
