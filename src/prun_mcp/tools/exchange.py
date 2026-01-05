"""Exchange/pricing-related MCP tools."""

import logging

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError
from prun_mcp.prun_lib.exchange import (
    InvalidExchangeError,
    get_exchange_all_async,
    get_exchange_prices_async,
)

logger = logging.getLogger(__name__)


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
    try:
        result = await get_exchange_prices_async(ticker, exchange)

        if not result["prices"] and result.get("not_found"):
            return [
                TextContent(
                    type="text",
                    text=f"No exchange data found for: {', '.join(result['not_found'])}",
                )
            ]

        return toon_encode(result)

    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]
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
    try:
        result = await get_exchange_all_async(exchange)
        return toon_encode(result)

    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while fetching exchange data")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
