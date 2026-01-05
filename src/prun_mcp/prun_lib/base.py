"""Base and permit calculation business logic."""


def calculate_area_limit(permits: int) -> int:
    """Calculate area limit for given number of permits.

    The formula is: 500 for the first permit, +250 for each additional permit.

    Args:
        permits: Number of base permits (1 or more).

    Returns:
        Maximum area in units. Returns 0 if permits <= 0.
    """
    if permits <= 0:
        return 0
    return 500 + max(0, permits - 1) * 250
