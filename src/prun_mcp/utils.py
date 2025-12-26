"""Utility functions for prun-mcp."""

import re
from typing import Any

# Fields containing camelCase names that should be prettified
NAME_FIELDS = {"Name", "CategoryName", "MaterialName", "CommodityName"}


def camel_to_title(text: str) -> str:
    """Convert camelCase to Title Case.

    Args:
        text: A camelCase string (e.g., "drinkingWater").

    Returns:
        Title Case string (e.g., "Drinking Water").

    Examples:
        >>> camel_to_title("drinkingWater")
        'Drinking Water'
        >>> camel_to_title("pioneerClothing")
        'Pioneer Clothing'
        >>> camel_to_title("advancedFuelRod")
        'Advanced Fuel Rod'
        >>> camel_to_title("aluminium")
        'Aluminium'
    """
    # Insert space before uppercase letters
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    # Capitalize first letter of each word
    return spaced.title()


def prettify_names(data: Any) -> Any:
    """Recursively transform camelCase name fields to Title Case.

    Transforms fields in NAME_FIELDS (Name, CategoryName, MaterialName,
    CommodityName) from camelCase to Title Case for human-readable output.

    Args:
        data: A dict, list, or primitive value to transform.

    Returns:
        Transformed data with prettified name fields.

    Examples:
        >>> prettify_names({"Name": "drinkingWater", "Ticker": "DW"})
        {'Name': 'Drinking Water', 'Ticker': 'DW'}
        >>> prettify_names([{"Name": "water"}, {"Name": "rations"}])
        [{'Name': 'Water'}, {'Name': 'Rations'}]
    """
    if isinstance(data, dict):
        return {
            k: camel_to_title(v) if k in NAME_FIELDS and isinstance(v, str) else prettify_names(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [prettify_names(item) for item in data]
    return data
