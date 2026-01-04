"""Exchange/pricing-related MCP tools."""

import asyncio
import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError, FIONotFoundError, get_fio_client
from prun_mcp.prun_lib import VALID_EXCHANGES
from prun_mcp.utils import prettify_names

logger = logging.getLogger(__name__)


def _validate_exchanges(exchange: str) -> list[str] | str:
    """Validate comma-separated exchanges. Returns list or error string."""
    exchanges = [e.strip().upper() for e in exchange.split(",")]
    invalid = [e for e in exchanges if e not in VALID_EXCHANGES]
    if invalid:
        valid_list = ", ".join(sorted(VALID_EXCHANGES))
        return f"Invalid exchange(s): {', '.join(invalid)}. Valid: {valid_list}"
    return exchanges


@mcp.tool()
async def get_exchange_prices(ticker: str, exchange: str) -> str | list[TextContent]:
    """Get current market prices with full order book for material(s).

    Args:
        ticker: Material ticker symbol(s). Can be single (e.g., "RAT")
                or comma-separated (e.g., "RAT,BSE,H2O").
        exchange: Exchange code(s). Can be single (e.g., "CI1")
                  or comma-separated (e.g., "CI1,NC1").
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.

    Returns:
        TOON-encoded price data including full order book (BuyingOrders,
        SellingOrders), bid/ask, supply/demand, and price statistics.
    """
    result = _validate_exchanges(exchange)
    if isinstance(result, str):
        return [TextContent(type="text", text=result)]
    exchanges = result

    try:
        client = get_fio_client()
        tickers = [t.strip().upper() for t in ticker.split(",")]

        async def fetch_one(t: str, ex: str) -> tuple[str, str, dict[str, Any] | None]:
            try:
                data = await client.get_exchange_info(t, ex)
                return (t, ex, data)
            except FIONotFoundError:
                return (t, ex, None)

        results = await asyncio.gather(
            *[fetch_one(t, ex) for t in tickers for ex in exchanges]
        )

        prices = []
        not_found = []

        for ticker_name, exchange_code, data in results:
            if data is None:
                not_found.append(f"{ticker_name}.{exchange_code}")
            else:
                prices.append(data)

        if not prices and not_found:
            return [
                TextContent(
                    type="text",
                    text=f"No exchange data found for: {', '.join(not_found)}",
                )
            ]

        output: dict[str, Any] = {"prices": prices}
        if not_found:
            output["not_found"] = not_found

        return toon_encode(prettify_names(output))

    except FIOApiError as e:
        logger.exception("FIO API error while fetching exchange prices")
        return [TextContent(type="text", text=f"FIO API error: {e}")]


@mcp.tool()
async def get_exchange_all(exchange: str) -> str | list[TextContent]:
    """Get summary prices for all materials on a specific exchange.

    Args:
        exchange: Exchange code(s). Can be single (e.g., "CI1")
                  or comma-separated (e.g., "CI1,NC1").
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.

    Returns:
        TOON-encoded list of all material prices on the exchange(s).
    """
    result = _validate_exchanges(exchange)
    if isinstance(result, str):
        return [TextContent(type="text", text=result)]
    exchanges = result

    try:
        client = get_fio_client()
        all_data = await client.get_all_exchange_data()

        exchange_set = set(exchanges)
        prices = [item for item in all_data if item.get("ExchangeCode") in exchange_set]

        return toon_encode(prettify_names({"prices": prices}))

    except FIOApiError as e:
        logger.exception("FIO API error while fetching exchange data")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
