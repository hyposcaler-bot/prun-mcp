"""Workforce consumption calculation business logic."""

from typing import Any, Protocol

# Workforce types in tier order (lowest to highest)
WORKFORCE_TYPES = ["Pioneers", "Settlers", "Technicians", "Engineers", "Scientists"]


class WorkforceNeedsProvider(Protocol):
    """Protocol for objects that can provide workforce needs."""

    def get_needs(self, workforce_type: str) -> list[dict[str, Any]] | None:
        """Get consumption needs for a workforce type.

        Args:
            workforce_type: Workforce type (e.g., "PIONEER", "SETTLER")

        Returns:
            List of material needs dicts with MaterialTicker and Amount keys,
            or None if not found.
        """
        ...


def normalize_workforce_type(workforce_type: str) -> str:
    """Normalize a workforce type name for cache lookup.

    Converts "Pioneers" -> "PIONEER", "Settlers" -> "SETTLER", etc.

    Args:
        workforce_type: Workforce type name (e.g., "Pioneers", "SETTLER")

    Returns:
        Normalized uppercase singular form (e.g., "PIONEER").
    """
    wf_upper = workforce_type.upper()
    if wf_upper.endswith("S"):
        wf_upper = wf_upper[:-1]
    return wf_upper


def calculate_workforce_consumption(
    workforce_counts: dict[str, int],
    needs_provider: WorkforceNeedsProvider,
) -> dict[str, float]:
    """Calculate daily material consumption for workforce.

    Args:
        workforce_counts: Dict mapping workforce type to worker count.
            Keys should match WORKFORCE_TYPES (e.g., "Pioneers", "Settlers").
        needs_provider: Object with get_needs() method (e.g., WorkforceCache).

    Returns:
        Dict mapping material ticker to daily consumption amount.
    """
    consumption: dict[str, float] = {}

    for wf_type, worker_count in workforce_counts.items():
        if worker_count <= 0:
            continue

        normalized_type = normalize_workforce_type(wf_type)
        needs = needs_provider.get_needs(normalized_type)
        if not needs:
            continue

        for need in needs:
            ticker = need.get("MaterialTicker", "")
            amount_per_100 = need.get("Amount", 0)
            if ticker and amount_per_100 > 0:
                daily_amount = (worker_count / 100) * amount_per_100
                consumption[ticker] = consumption.get(ticker, 0) + daily_amount

    return consumption


def get_workforce_from_building(
    building: dict[str, Any],
    count: int = 1,
) -> dict[str, int]:
    """Extract workforce counts from a building dict.

    Args:
        building: Building dict with workforce type keys (e.g., "Pioneers": 10).
        count: Number of buildings (multiplies all workforce counts).

    Returns:
        Dict mapping workforce type to total worker count.
    """
    workforce: dict[str, int] = {}
    for wf_type in WORKFORCE_TYPES:
        workers = building.get(wf_type, 0)
        if workers > 0:
            workforce[wf_type] = workers * count
    return workforce


def aggregate_workforce(
    *workforce_dicts: dict[str, int],
) -> dict[str, int]:
    """Aggregate multiple workforce dicts into one.

    Args:
        *workforce_dicts: Variable number of workforce count dicts.

    Returns:
        Combined dict with summed worker counts per type.
    """
    total: dict[str, int] = {}
    for wf_dict in workforce_dicts:
        for wf_type, count in wf_dict.items():
            total[wf_type] = total.get(wf_type, 0) + count
    return total


def get_consumable_tickers(
    workforce_counts: dict[str, int],
    needs_provider: WorkforceNeedsProvider,
) -> set[str]:
    """Get the set of material tickers consumed by a workforce.

    Useful for fetching prices before calculating consumption costs.

    Args:
        workforce_counts: Dict mapping workforce type to worker count.
        needs_provider: Object with get_needs() method.

    Returns:
        Set of material tickers that would be consumed.
    """
    tickers: set[str] = set()

    for wf_type, worker_count in workforce_counts.items():
        if worker_count <= 0:
            continue

        normalized_type = normalize_workforce_type(wf_type)
        needs = needs_provider.get_needs(normalized_type)
        if not needs:
            continue

        for need in needs:
            ticker = need.get("MaterialTicker", "")
            if ticker:
                tickers.add(ticker)

    return tickers
