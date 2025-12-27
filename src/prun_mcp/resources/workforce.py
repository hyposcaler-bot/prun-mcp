"""Workforce data and MCP resources."""

from prun_mcp.app import mcp

# Workforce types - canonical source (ordered by tier, lowest to highest)
WORKFORCE_TYPES = ["Pioneers", "Settlers", "Technicians", "Engineers", "Scientists"]

# Habitation capacity per building type - canonical source
HABITATION_CAPACITY: dict[str, dict[str, int]] = {
    "HB1": {"Pioneers": 100},
    "HB2": {"Settlers": 100},
    "HB3": {"Technicians": 100},
    "HB4": {"Engineers": 100},
    "HB5": {"Scientists": 100},
    "HBB": {"Pioneers": 75, "Settlers": 75},
    "HBC": {"Settlers": 75, "Technicians": 75},
    "HBM": {"Technicians": 75, "Engineers": 75},
    "HBL": {"Engineers": 75, "Scientists": 75},
}

VALID_HABITATION = set(HABITATION_CAPACITY.keys())


@mcp.resource("workforce://types")
def get_workforce_types() -> str:
    """List all workforce types in tier order (lowest to highest).

    Returns:
        Newline-separated list of workforce types.
    """
    return "\n".join(WORKFORCE_TYPES)


def format_habitation_capacity() -> str:
    """Format habitation capacity for display.

    Returns:
        Human-readable table of habitation buildings and capacities.
    """
    lines = ["Building  Capacity"]
    lines.append("-" * 40)
    for building, capacity in HABITATION_CAPACITY.items():
        cap_str = ", ".join(f"{k}: {v}" for k, v in capacity.items())
        lines.append(f"{building}       {cap_str}")
    return "\n".join(lines)


@mcp.resource("workforce://habitation")
def get_habitation_capacity() -> str:
    """List all habitation buildings with workforce capacities.

    Returns:
        Human-readable table of habitation buildings showing
        building ticker and workforce capacity by type.
    """
    return format_habitation_capacity()
