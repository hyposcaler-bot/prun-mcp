"""Utility functions for prun-mcp."""

import asyncio
import re
from typing import Any

from prun_mcp.fio import FIONotFoundError, get_fio_client

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
            k: camel_to_title(v)
            if k in NAME_FIELDS and isinstance(v, str)
            else prettify_names(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [prettify_names(item) for item in data]
    return data


async def fetch_prices(
    tickers: list[str], exchange: str
) -> dict[str, dict[str, float | None]]:
    """Fetch Ask and Bid prices for multiple tickers from an exchange.

    Args:
        tickers: List of material ticker symbols.
        exchange: Exchange code (e.g., "CI1").

    Returns:
        Dict mapping ticker to {"ask": price, "bid": price}.
        Prices are None if the material is not traded on the exchange.
    """
    client = get_fio_client()

    async def fetch_one(ticker: str) -> tuple[str, dict[str, float | None]]:
        try:
            data = await client.get_exchange_info(ticker, exchange)
            return (ticker, {"ask": data.get("Ask"), "bid": data.get("Bid")})
        except FIONotFoundError:
            return (ticker, {"ask": None, "bid": None})

    results = await asyncio.gather(*[fetch_one(t) for t in tickers])
    return dict(results)
