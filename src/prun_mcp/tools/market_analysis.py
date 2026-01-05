"""Market analysis MCP tools for trading decisions."""

import logging

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError
from prun_mcp.prun_lib.exchange import InvalidExchangeError
from prun_mcp.prun_lib.market import (
    MarketError,
    analyze_fill_cost_async,
    get_market_summary_async,
    get_order_book_depth_async,
    get_price_history_async,
    get_price_history_summary_async,
)

logger = logging.getLogger(__name__)


@mcp.tool()
async def get_market_summary(ticker: str, exchange: str) -> str | list[TextContent]:
    """Get a quick market snapshot with actionable warnings.

    Args:
        ticker: Material ticker symbol(s). Single (e.g., "RAT") or
                comma-separated (e.g., "RAT,COF,SF").
        exchange: Exchange code (e.g., "CI1"). Single exchange only.
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.

    Returns:
        Plain text market summary with bid/ask, spread, supply/demand,
        and warnings about market conditions.
    """
    try:
        result = await get_market_summary_async(ticker, exchange)
        return result

    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while fetching market summary")
        return [TextContent(type="text", text=f"FIO API error: {e}")]


@mcp.tool()
async def analyze_fill_cost(
    ticker: str, exchange: str, quantity: int, direction: str
) -> str | list[TextContent]:
    """Calculate expected cost/proceeds for a specific quantity.

    Walks the order book to account for slippage when executing a trade.

    Args:
        ticker: Material ticker symbol (e.g., "RAT"). Single ticker only.
        exchange: Exchange code (e.g., "CI1").
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.
        quantity: Number of units to buy or sell.
        direction: "buy" or "sell".

    Returns:
        TOON-encoded fill analysis including fills breakdown, VWAP,
        slippage, and limit price recommendations.
    """
    try:
        result = await analyze_fill_cost_async(ticker, exchange, quantity, direction)

        # Check if error returned (not raised)
        if "error" in result:
            return [TextContent(type="text", text=result["error"])]

        return toon_encode(result)

    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]
    except MarketError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while analyzing fill cost")
        return [TextContent(type="text", text=f"FIO API error: {e}")]


@mcp.tool()
async def get_price_history_summary(
    ticker: str, exchange: str, days: int = 7
) -> str | list[TextContent]:
    """Compare current market conditions to historical norms.

    Args:
        ticker: Material ticker symbol(s). Single (e.g., "RAT") or
                comma-separated (e.g., "RAT,COF,SF").
        exchange: Exchange code (e.g., "CI1"). Single exchange only.
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.
        days: Historical lookback period in days. Valid: 1-30. Default: 7.

    Returns:
        Plain text historical comparison with current vs. historical
        prices, spreads, volume, and insights.
    """
    try:
        result = await get_price_history_summary_async(ticker, exchange, days)
        return result

    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]
    except MarketError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while fetching price history summary")
        return [TextContent(type="text", text=f"FIO API error: {e}")]


@mcp.tool()
async def get_order_book_depth(
    ticker: str, exchange: str, side: str = "both", levels: int = 20
) -> str | list[TextContent]:
    """Get full order book in TOON tabular format.

    Args:
        ticker: Material ticker symbol(s). Single (e.g., "RAT") or
                comma-separated (e.g., "RAT,COF").
        exchange: Exchange code (e.g., "CI1"). Single exchange only.
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.
        side: "buy" (bids), "sell" (asks), or "both". Default: "both".
        levels: Maximum price levels per side. Capped to 10 for multi-ticker.
                Valid: 1-100. Default: 20.

    Returns:
        TOON-encoded order book with aggregated levels and cumulative
        calculations for cost/proceeds analysis.
    """
    try:
        result = await get_order_book_depth_async(ticker, exchange, side, levels)

        # Check if error returned (not raised)
        if "error" in result:
            return [TextContent(type="text", text=result["error"])]

        return toon_encode(result)

    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]
    except MarketError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while fetching order book depth")
        return [TextContent(type="text", text=f"FIO API error: {e}")]


@mcp.tool()
async def get_price_history(
    ticker: str, exchange: str, days: int = 7
) -> str | list[TextContent]:
    """Get historical price data in TOON tabular format.

    Args:
        ticker: Material ticker symbol(s). Single (e.g., "RAT") or
                comma-separated (e.g., "RAT,COF,SF").
        exchange: Exchange code (e.g., "CI1"). Single exchange only.
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.
        days: Historical lookback period in days. Valid: 1-30. Default: 7.

    Returns:
        TOON-encoded time series with daily OHLCV data and summary
        statistics for trend analysis.
    """
    try:
        result = await get_price_history_async(ticker, exchange, days)

        # Check if error returned (not raised)
        if "error" in result:
            return [TextContent(type="text", text=result["error"])]

        return toon_encode(result)

    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]
    except MarketError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while fetching price history")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
