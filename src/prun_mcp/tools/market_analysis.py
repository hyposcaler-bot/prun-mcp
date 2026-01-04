"""Market analysis MCP tools for trading decisions."""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError, FIONotFoundError, get_fio_client
from prun_mcp.prun_lib import VALID_EXCHANGES
from prun_mcp.utils import prettify_names

logger = logging.getLogger(__name__)

# Implementation constants
SPREAD_WARNING_THRESHOLD = 5.0  # Percentage
THIN_DEPTH_THRESHOLD = 50  # Units
SUPPLY_DEMAND_IMBALANCE = 3.0  # Ratio
MULTI_TICKER_LEVEL_CAP = 10  # Levels per ticker when multiple requested
MM_PROXIMITY_THRESHOLD = 0.05  # 5% - warn when price is within this of MM

MS_PER_DAY = 24 * 60 * 60 * 1000


def _format_number(n: float | int | None, decimals: int = 2) -> str:
    """Format a number with commas and optional decimals."""
    if n is None:
        return "N/A"
    if isinstance(n, int) or n == int(n):
        return f"{int(n):,}"
    return f"{n:,.{decimals}f}"


def _aggregate_orders_by_price(
    orders: list[dict[str, Any]], descending: bool = False
) -> list[dict[str, Any]]:
    """Aggregate orders at the same price level.

    Args:
        orders: List of order dicts with ItemCount and ItemCost keys.
        descending: If True, sort by price descending (for bids).

    Returns:
        List of aggregated orders sorted by price.
    """
    price_levels: dict[float, int] = defaultdict(int)
    for order in orders:
        price = order.get("ItemCost") or 0
        count = order.get("ItemCount") or 0
        if price > 0 and count > 0:
            price_levels[price] += count

    result = [{"price": price, "units": units} for price, units in price_levels.items()]
    result.sort(key=lambda x: x["price"], reverse=descending)
    return result


def _generate_market_warnings(
    data: dict[str, Any], ticker: str | None = None
) -> list[str]:
    """Generate warning messages based on market conditions.

    Args:
        data: Exchange data with Bid, Ask, Supply, Demand, etc.
        ticker: Optional ticker prefix for multi-ticker output.

    Returns:
        List of warning strings.
    """
    warnings = []
    prefix = f"{ticker}: " if ticker else ""

    bid = data.get("Bid")
    ask = data.get("Ask")
    supply = data.get("Supply", 0)
    demand = data.get("Demand", 0)

    # Check for missing orders
    if bid is None:
        warnings.append(f"{prefix}No buy orders — cannot sell at market")
    if ask is None:
        warnings.append(f"{prefix}No sell orders — cannot buy at market")

    # Check spread
    if bid is not None and ask is not None and bid > 0:
        spread_pct = ((ask - bid) / bid) * 100
        if spread_pct > SPREAD_WARNING_THRESHOLD:
            warnings.append(
                f"{prefix}Wide spread ({spread_pct:.1f}% > {SPREAD_WARNING_THRESHOLD:.0f}%) "
                "— consider limit orders over market orders"
            )

    # Check depth at bid/ask
    buying_orders = data.get("BuyingOrders", [])
    selling_orders = data.get("SellingOrders", [])

    if bid is not None:
        bid_depth = sum(
            o.get("ItemCount") or 0 for o in buying_orders if o.get("ItemCost") == bid
        )
        if 0 < bid_depth < THIN_DEPTH_THRESHOLD:
            warnings.append(
                f"{prefix}Thin bid depth ({bid_depth} units) — "
                f"selling >{bid_depth} units will experience significant slippage"
            )

    if ask is not None:
        ask_depth = sum(
            o.get("ItemCount") or 0 for o in selling_orders if o.get("ItemCost") == ask
        )
        if 0 < ask_depth < THIN_DEPTH_THRESHOLD:
            warnings.append(
                f"{prefix}Thin ask depth ({ask_depth} units) — "
                f"buying >{ask_depth} units will experience significant slippage"
            )

    # Check supply/demand imbalance
    if demand > 0:
        ratio = supply / demand
        if ratio > SUPPLY_DEMAND_IMBALANCE:
            warnings.append(
                f"{prefix}Heavy supply pressure ({ratio:.1f}x) — "
                "expect downward price pressure"
            )
        elif ratio < 1 / SUPPLY_DEMAND_IMBALANCE:
            warnings.append(
                f"{prefix}Heavy demand pressure ({ratio:.2f}x) — "
                "expect upward price pressure"
            )

    # Check proximity to Market Maker prices
    mm_buy = data.get("MMBuy")
    mm_sell = data.get("MMSell")

    if mm_sell is not None and ask is not None:
        ceiling_threshold = mm_sell * (1 - MM_PROXIMITY_THRESHOLD)
        if ask >= ceiling_threshold:
            warnings.append(
                f"{prefix}Price near MM ceiling ({_format_number(ask)} vs "
                f"{_format_number(mm_sell)}) — limited upside"
            )

    if mm_buy is not None and bid is not None:
        floor_threshold = mm_buy * (1 + MM_PROXIMITY_THRESHOLD)
        if bid <= floor_threshold:
            warnings.append(
                f"{prefix}Price near MM floor ({_format_number(bid)} vs "
                f"{_format_number(mm_buy)}) — limited downside"
            )

    return warnings


def _format_market_summary_section(
    ticker: str, exchange: str, data: dict[str, Any]
) -> str:
    """Format a single material's market summary section.

    Args:
        ticker: Material ticker.
        exchange: Exchange code.
        data: Exchange data.

    Returns:
        Formatted plain text section.
    """
    bid = data.get("Bid")
    ask = data.get("Ask")
    supply = data.get("Supply", 0)
    demand = data.get("Demand", 0)

    # Calculate derived values
    bid_str = _format_number(bid) if bid is not None else "N/A"
    ask_str = _format_number(ask) if ask is not None else "N/A"

    # Get depth at best bid/ask
    buying_orders = data.get("BuyingOrders", [])
    selling_orders = data.get("SellingOrders", [])

    bid_depth = (
        sum(o.get("ItemCount") or 0 for o in buying_orders if o.get("ItemCost") == bid)
        if bid is not None
        else 0
    )
    ask_depth = (
        sum(o.get("ItemCount") or 0 for o in selling_orders if o.get("ItemCost") == ask)
        if ask is not None
        else 0
    )

    lines = [f"{ticker} on {exchange}:"]

    # Bid/Ask line
    bid_part = f"Bid: {bid_str} ({_format_number(bid_depth)} units)"
    ask_part = f"Ask: {ask_str} ({_format_number(ask_depth)} units)"
    lines.append(f"{bid_part} | {ask_part}")

    # Spread and mid
    if bid is not None and ask is not None:
        spread = ask - bid
        spread_pct = (spread / bid * 100) if bid > 0 else 0
        mid = (bid + ask) / 2
        lines.append(
            f"Spread: {_format_number(spread)} ({spread_pct:.1f}%) | "
            f"Mid: {_format_number(mid)}"
        )
    else:
        lines.append("Spread: N/A | Mid: N/A")

    # Supply/Demand
    if demand > 0:
        ratio = supply / demand
        market_type = "seller's market" if ratio > 1 else "buyer's market"
        lines.append(
            f"Supply: {_format_number(supply)} | Demand: {_format_number(demand)} | "
            f"Ratio: {ratio:.1f}x ({market_type})"
        )
    else:
        lines.append(
            f"Supply: {_format_number(supply)} | Demand: {_format_number(demand)}"
        )

    # Market Maker prices (if present)
    mm_buy = data.get("MMBuy")
    mm_sell = data.get("MMSell")
    if mm_buy is not None or mm_sell is not None:
        mm_parts = []
        if mm_buy is not None:
            mm_parts.append(f"Buy {_format_number(mm_buy)}")
        if mm_sell is not None:
            mm_parts.append(f"Sell {_format_number(mm_sell)}")
        lines.append(f"MM: {' | '.join(mm_parts)}")

    return "\n".join(lines)


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
    exchange = exchange.strip().upper()
    if exchange not in VALID_EXCHANGES:
        valid_list = ", ".join(sorted(VALID_EXCHANGES))
        return [
            TextContent(
                type="text",
                text=f"Invalid exchange: {exchange}. Valid: {valid_list}",
            )
        ]

    tickers = [t.strip().upper() for t in ticker.split(",")]
    client = get_fio_client()

    async def fetch_one(t: str) -> tuple[str, dict[str, Any] | None]:
        try:
            data = await client.get_exchange_info(t, exchange)
            return (t, data)
        except FIONotFoundError:
            return (t, None)

    try:
        results = await asyncio.gather(*[fetch_one(t) for t in tickers])
    except FIOApiError as e:
        logger.exception("FIO API error while fetching market summary")
        return [TextContent(type="text", text=f"FIO API error: {e}")]

    sections = []
    all_warnings = []
    not_found = []
    is_multi = len(tickers) > 1

    for t, data in results:
        if data is None:
            not_found.append(t)
            continue

        section = _format_market_summary_section(t, exchange, data)
        sections.append(section)

        warnings = _generate_market_warnings(data, t if is_multi else None)
        all_warnings.extend(warnings)

    if not sections and not_found:
        return [
            TextContent(
                type="text",
                text=f"No exchange data for: {', '.join(not_found)}",
            )
        ]

    # Build output
    output_parts = []

    if is_multi:
        output_parts.append("\n\n---\n\n".join(sections))
    else:
        output_parts.append(sections[0] if sections else "")

    if all_warnings:
        output_parts.append("\nWarnings:")
        for w in all_warnings:
            output_parts.append(f"• {w}")

    if not_found:
        output_parts.append(f"\nNot found: {', '.join(not_found)}")

    return "\n".join(output_parts)


def _walk_order_book(orders: list[dict[str, Any]], quantity: int) -> dict[str, Any]:
    """Walk an order book to fill a quantity.

    Args:
        orders: Aggregated orders sorted by price (asc for sells, desc for buys).
        quantity: Units to fill.

    Returns:
        Dict with fill information.
    """
    fills = []
    cumulative_units = 0
    cumulative_cost = 0.0
    best_price = orders[0]["price"] if orders else None
    worst_price = None

    for order in orders:
        if cumulative_units >= quantity:
            break

        price = order["price"]
        available = order["units"]
        needed = quantity - cumulative_units
        take = min(available, needed)

        cumulative_units += take
        cumulative_cost += take * price
        worst_price = price

        fills.append(
            {
                "price": price,
                "units": take,
                "cumulative": cumulative_units,
                "cumulative_cost": round(cumulative_cost, 2),
            }
        )

    can_fill = cumulative_units >= quantity
    fill_quantity = cumulative_units
    unfilled = max(0, quantity - cumulative_units)
    vwap = cumulative_cost / fill_quantity if fill_quantity > 0 else 0
    slippage = abs(vwap - best_price) if best_price else 0
    slippage_pct = (slippage / best_price * 100) if best_price and best_price > 0 else 0

    return {
        "can_fill": can_fill,
        "fill_quantity": fill_quantity,
        "unfilled": unfilled,
        "best_price": best_price,
        "worst_price": worst_price,
        "vwap": round(vwap, 2),
        "total_cost": round(cumulative_cost, 2),
        "slippage_from_best": round(slippage, 2),
        "slippage_pct": round(slippage_pct, 2),
        "depth_consumed": len(fills),
        "fills": fills,
    }


def _generate_fill_recommendations(
    fills: list[dict[str, Any]], quantity: int
) -> list[str]:
    """Generate limit price recommendations at inflection points.

    Args:
        fills: List of fill dicts with price, units, cumulative.
        quantity: Total requested quantity.

    Returns:
        List of recommendation strings.
    """
    if not fills:
        return []

    recommendations = []
    best_fill = fills[0]

    # Best price tier
    best_pct = (best_fill["cumulative"] / quantity * 100) if quantity > 0 else 0
    recommendations.append(
        f"Limit at {best_fill['price']} would fill {best_fill['cumulative']} units "
        f"({best_pct:.0f}%) at best available price"
    )

    # Find 50% and 80% tiers if they exist
    for target_pct in [50, 80]:
        target_units = quantity * target_pct / 100
        for fill in fills:
            if fill["cumulative"] >= target_units:
                if fill["price"] != best_fill["price"]:
                    fill_pct = fill["cumulative"] / quantity * 100
                    # Calculate VWAP to this point
                    vwap_here = fill["cumulative_cost"] / fill["cumulative"]
                    improvement = abs(
                        vwap_here
                        - fills[-1]["cumulative_cost"] / fills[-1]["cumulative"]
                    )
                    improvement_pct = (
                        (improvement / vwap_here * 100) if vwap_here > 0 else 0
                    )
                    recommendations.append(
                        f"Limit at {fill['price']} would fill {fill['cumulative']} units "
                        f"({fill_pct:.0f}%) with {improvement_pct:.2f}% better avg price"
                    )
                break

    # Full fill at market
    if fills and fills[-1]["cumulative"] >= quantity:
        final_vwap = fills[-1]["cumulative_cost"] / fills[-1]["cumulative"]
        slippage = abs(final_vwap - best_fill["price"])
        slippage_pct = (
            (slippage / best_fill["price"] * 100) if best_fill["price"] > 0 else 0
        )
        recommendations.append(
            f"Market order fills all {quantity} at {final_vwap:.2f} avg "
            f"({slippage_pct:.2f}% slippage)"
        )

    return recommendations


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
    exchange = exchange.strip().upper()
    if exchange not in VALID_EXCHANGES:
        valid_list = ", ".join(sorted(VALID_EXCHANGES))
        return [
            TextContent(
                type="text",
                text=f"Invalid exchange: {exchange}. Valid: {valid_list}",
            )
        ]

    direction = direction.strip().lower()
    if direction not in ("buy", "sell"):
        return [
            TextContent(
                type="text",
                text=f"Invalid direction: {direction}. Must be 'buy' or 'sell'.",
            )
        ]

    if quantity <= 0:
        return [
            TextContent(
                type="text",
                text=f"Invalid quantity: {quantity}. Must be positive.",
            )
        ]

    ticker = ticker.strip().upper()
    client = get_fio_client()

    try:
        data = await client.get_exchange_info(ticker, exchange)
    except FIONotFoundError:
        return [
            TextContent(
                type="text",
                text=f"No exchange data for {ticker}.{exchange}",
            )
        ]
    except FIOApiError as e:
        logger.exception("FIO API error while analyzing fill cost")
        return [TextContent(type="text", text=f"FIO API error: {e}")]

    # Get the relevant order book side
    if direction == "buy":
        raw_orders = data.get("SellingOrders", [])
        orders = _aggregate_orders_by_price(raw_orders, descending=False)  # Ascending
    else:
        raw_orders = data.get("BuyingOrders", [])
        orders = _aggregate_orders_by_price(raw_orders, descending=True)  # Descending

    if not orders:
        side = "sell" if direction == "buy" else "buy"
        return [
            TextContent(
                type="text",
                text=f"No {side} orders available for {ticker}.{exchange}",
            )
        ]

    # Walk the order book
    fill_result = _walk_order_book(orders, quantity)

    # Calculate remaining at worst price
    remaining_at_worst = 0
    if fill_result["worst_price"]:
        for order in orders:
            if order["price"] == fill_result["worst_price"]:
                # Find how much was taken from this level
                for fill in fill_result["fills"]:
                    if fill["price"] == fill_result["worst_price"]:
                        remaining_at_worst = order["units"] - fill["units"]
                        break
                break

    # Generate recommendations
    recommendations = _generate_fill_recommendations(fill_result["fills"], quantity)

    # Build result
    result: dict[str, Any] = {
        "ticker": ticker,
        "exchange": exchange,
        "direction": direction,
        "quantity": quantity,
        "can_fill": fill_result["can_fill"],
        "fill_quantity": fill_result["fill_quantity"],
        "unfilled": fill_result["unfilled"],
        "best_price": fill_result["best_price"],
        "worst_price": fill_result["worst_price"],
        "vwap": fill_result["vwap"],
        "total_cost": fill_result["total_cost"],
        "slippage_from_best": fill_result["slippage_from_best"],
        "slippage_pct": fill_result["slippage_pct"],
        "depth_consumed": fill_result["depth_consumed"],
        "remaining_at_worst": remaining_at_worst,
        "fills": fill_result["fills"],
        "recommendations": recommendations,
    }

    # Add warnings for partial fills
    if not fill_result["can_fill"]:
        total_available = sum(o["units"] for o in orders)
        pct_fillable = fill_result["fill_quantity"] / quantity * 100
        result["warnings"] = [
            f"Insufficient {'supply' if direction == 'buy' else 'demand'} — "
            f"can only fill {fill_result['fill_quantity']} of {quantity} units "
            f"({pct_fillable:.0f}%)",
            f"Full order would clear entire {'sell' if direction == 'buy' else 'buy'} side"
            if fill_result["fill_quantity"] >= total_available
            else None,
        ]
        result["warnings"] = [w for w in result["warnings"] if w]

    return toon_encode(prettify_names(result))


def _calculate_price_stats(candles: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate statistics from price history candles.

    Args:
        candles: List of OHLCV candles.

    Returns:
        Dict with statistical summaries.
    """
    if not candles:
        return {}

    closes = [c.get("Close", 0) for c in candles if c.get("Close")]
    highs = [c.get("High", 0) for c in candles if c.get("High")]
    lows = [c.get("Low", 0) for c in candles if c.get("Low")]
    volumes = [c.get("Traded", 0) for c in candles]

    avg_price = sum(closes) / len(closes) if closes else 0
    high = max(highs) if highs else 0
    low = min(lows) if lows else 0
    total_volume = sum(volumes)
    avg_daily_volume = total_volume / len(candles) if candles else 0

    # Calculate price change from first to last
    first_close = closes[-1] if closes else 0  # Candles are most recent first
    last_close = closes[0] if closes else 0
    price_change = last_close - first_close
    price_change_pct = (price_change / first_close * 100) if first_close > 0 else 0

    return {
        "avg_price": round(avg_price, 2),
        "high": high,
        "low": low,
        "total_volume": total_volume,
        "avg_daily_volume": round(avg_daily_volume, 0),
        "price_change": round(price_change, 2),
        "price_change_pct": round(price_change_pct, 2),
        "num_candles": len(candles),
    }


def _generate_history_insights(
    current_mid: float | None,
    stats: dict[str, Any],
    ticker: str | None = None,
) -> list[str]:
    """Generate insights comparing current conditions to history.

    Args:
        current_mid: Current mid price.
        stats: Historical statistics.
        ticker: Optional ticker prefix.

    Returns:
        List of insight strings.
    """
    insights = []
    prefix = f"{ticker}: " if ticker else ""

    avg_price = stats.get("avg_price", 0)

    if current_mid is not None and avg_price > 0:
        price_vs_avg = ((current_mid - avg_price) / avg_price) * 100

        if abs(price_vs_avg) < 3:
            insights.append(
                f"{prefix}Current price ({current_mid:.0f}) is near historical "
                f"average ({avg_price:.0f}) — fair value"
            )
        elif price_vs_avg > 5:
            insights.append(
                f"{prefix}Current price ({current_mid:.0f}) is {price_vs_avg:.1f}% "
                f"ABOVE historical average ({avg_price:.0f}) — consider waiting to buy"
            )
        elif price_vs_avg < -5:
            insights.append(
                f"{prefix}Current price ({current_mid:.0f}) is {abs(price_vs_avg):.1f}% "
                f"BELOW historical average ({avg_price:.0f}) — good buying opportunity"
            )
        else:
            direction = "above" if price_vs_avg > 0 else "below"
            insights.append(
                f"{prefix}Current price ({current_mid:.0f}) is {abs(price_vs_avg):.1f}% "
                f"{direction} avg — slightly {'elevated' if price_vs_avg > 0 else 'depressed'}"
            )

    avg_daily = stats.get("avg_daily_volume", 0)
    if avg_daily < 100:
        insights.append(
            f"{prefix}Low volume market (~{avg_daily:.0f}/day) — "
            "large orders will move the market"
        )

    return insights


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
    exchange = exchange.strip().upper()
    if exchange not in VALID_EXCHANGES:
        valid_list = ", ".join(sorted(VALID_EXCHANGES))
        return [
            TextContent(
                type="text",
                text=f"Invalid exchange: {exchange}. Valid: {valid_list}",
            )
        ]

    if days < 1 or days > 30:
        return [
            TextContent(
                type="text",
                text=f"Invalid days: {days}. Must be 1-30.",
            )
        ]

    tickers = [t.strip().upper() for t in ticker.split(",")]
    client = get_fio_client()

    async def fetch_both(t: str) -> tuple[str, dict | None, list | None]:
        """Fetch both current and historical data for a ticker."""
        current = None
        history = None

        try:
            current = await client.get_exchange_info(t, exchange)
        except FIONotFoundError:
            pass

        try:
            history = await client.get_price_history(t, exchange)
        except FIONotFoundError:
            pass

        return (t, current, history)

    try:
        results = await asyncio.gather(*[fetch_both(t) for t in tickers])
    except FIOApiError as e:
        logger.exception("FIO API error while fetching price history summary")
        return [TextContent(type="text", text=f"FIO API error: {e}")]

    sections = []
    not_found = []
    is_multi = len(tickers) > 1

    for t, current, history in results:
        if current is None and history is None:
            not_found.append(t)
            continue

        lines = [f"{t} on {exchange} ({days}-day history):"]
        lines.append("")

        # Current conditions
        bid = current.get("Bid") if current else None
        ask = current.get("Ask") if current else None
        current_mid = (bid + ask) / 2 if bid and ask else None
        current_spread_pct = (
            ((ask - bid) / bid * 100) if bid and ask and bid > 0 else None
        )

        if current_mid is not None:
            spread_str = f"{current_spread_pct:.1f}%" if current_spread_pct else "N/A"
            lines.append(f"Current: {current_mid:.1f} mid | Spread: {spread_str}")
        else:
            lines.append("Current: No current market data")

        # Filter history to requested days
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        cutoff_ms = now_ms - (days * MS_PER_DAY)

        daily_candles = []
        if history:
            daily_candles = [
                c
                for c in history
                if c.get("Interval") == "DAY_ONE"
                and c.get("DateEpochMs", 0) >= cutoff_ms
            ]

        if daily_candles:
            stats = _calculate_price_stats(daily_candles)
            avg_price = stats.get("avg_price", 0)
            high = stats.get("high", 0)
            low = stats.get("low", 0)
            total_vol = stats.get("total_volume", 0)
            avg_daily = stats.get("avg_daily_volume", 0)

            lines.append(
                f"Historical: avg {avg_price:.1f} | range {low:.0f}–{high:.0f}"
            )
            lines.append(
                f"Volume: ~{avg_daily:,.0f}/day ({total_vol:,} total, "
                f"{stats.get('num_candles', 0)} days)"
            )

            # Insights
            insights = _generate_history_insights(
                current_mid, stats, t if is_multi else None
            )
            if insights:
                lines.append("")
                lines.append("Insights:")
                for insight in insights:
                    lines.append(f"• {insight}")
        else:
            lines.append("Historical: No history available for this period")

        sections.append("\n".join(lines))

    if not sections and not_found:
        return [
            TextContent(
                type="text",
                text=f"No data for: {', '.join(not_found)}",
            )
        ]

    # Build output
    output_parts = []

    if is_multi:
        output_parts.append("\n\n---\n\n".join(sections))
    else:
        output_parts.append(sections[0] if sections else "")

    if not_found:
        output_parts.append(f"\nNot found: {', '.join(not_found)}")

    return "\n".join(output_parts)


def _build_order_book_levels(
    orders: list[dict[str, Any]], levels: int, is_sell: bool
) -> list[dict[str, Any]]:
    """Build order book levels with cumulative calculations.

    Args:
        orders: Aggregated orders sorted appropriately.
        levels: Maximum levels to return.
        is_sell: True for sell orders (cumulative cost), False for buys (proceeds).

    Returns:
        List of level dicts with cumulative calculations.
    """
    result = []
    cumulative_units = 0
    cumulative_value = 0.0

    for order in orders[:levels]:
        price = order["price"]
        units = order["units"]

        cumulative_units += units
        cumulative_value += price * units
        vwap = cumulative_value / cumulative_units if cumulative_units > 0 else 0

        level = {
            "price": price,
            "units": units,
            "cumulative_units": cumulative_units,
            "vwap_to_here": round(vwap, 2),
        }

        if is_sell:
            level["cumulative_cost"] = round(cumulative_value, 2)
        else:
            level["cumulative_proceeds"] = round(cumulative_value, 2)

        result.append(level)

    return result


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
    exchange = exchange.strip().upper()
    if exchange not in VALID_EXCHANGES:
        valid_list = ", ".join(sorted(VALID_EXCHANGES))
        return [
            TextContent(
                type="text",
                text=f"Invalid exchange: {exchange}. Valid: {valid_list}",
            )
        ]

    side = side.strip().lower()
    if side not in ("buy", "sell", "both"):
        return [
            TextContent(
                type="text",
                text=f"Invalid side: {side}. Must be 'buy', 'sell', or 'both'.",
            )
        ]

    if levels < 1 or levels > 100:
        return [
            TextContent(
                type="text",
                text=f"Invalid levels: {levels}. Must be 1-100.",
            )
        ]

    tickers = [t.strip().upper() for t in ticker.split(",")]
    is_multi = len(tickers) > 1

    # Cap levels for multi-ticker
    effective_levels = min(levels, MULTI_TICKER_LEVEL_CAP) if is_multi else levels

    client = get_fio_client()

    async def fetch_one(t: str) -> tuple[str, dict[str, Any] | None]:
        try:
            data = await client.get_exchange_info(t, exchange)
            return (t, data)
        except FIONotFoundError:
            return (t, None)

    try:
        results = await asyncio.gather(*[fetch_one(t) for t in tickers])
    except FIOApiError as e:
        logger.exception("FIO API error while fetching order book depth")
        return [TextContent(type="text", text=f"FIO API error: {e}")]

    order_books = []
    not_found = []

    for t, data in results:
        if data is None:
            not_found.append(t)
            continue

        book: dict[str, Any] = {
            "ticker": t,
            "exchange": exchange,
        }

        if is_multi:
            book["levels_returned"] = effective_levels

        bid = data.get("Bid")
        ask = data.get("Ask")

        # Build sell side (asks)
        if side in ("sell", "both"):
            sell_orders = _aggregate_orders_by_price(
                data.get("SellingOrders", []), descending=False
            )
            book["sell_orders"] = _build_order_book_levels(
                sell_orders, effective_levels, is_sell=True
            )

        # Build buy side (bids)
        if side in ("buy", "both"):
            buy_orders = _aggregate_orders_by_price(
                data.get("BuyingOrders", []), descending=True
            )
            book["buy_orders"] = _build_order_book_levels(
                buy_orders, effective_levels, is_sell=False
            )

        # Summary
        spread = (ask - bid) if bid and ask else None
        spread_pct = ((spread / bid) * 100) if spread and bid and bid > 0 else None

        book["summary"] = {
            "best_bid": bid,
            "best_ask": ask,
            "spread": round(spread, 2) if spread else None,
            "spread_pct": round(spread_pct, 2) if spread_pct else None,
            "total_bid_depth": data.get("Demand", 0),
            "total_ask_depth": data.get("Supply", 0),
            "mm_buy": data.get("MMBuy"),
            "mm_sell": data.get("MMSell"),
        }

        order_books.append(book)

    if not order_books and not_found:
        return [
            TextContent(
                type="text",
                text=f"No exchange data for: {', '.join(not_found)}",
            )
        ]

    # Build result
    if is_multi:
        result: dict[str, Any] = {"order_books": order_books}
        if not_found:
            result["not_found"] = not_found
    else:
        result = order_books[0] if order_books else {}
        if not_found:
            result["not_found"] = not_found

    return toon_encode(prettify_names(result))


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
    exchange = exchange.strip().upper()
    if exchange not in VALID_EXCHANGES:
        valid_list = ", ".join(sorted(VALID_EXCHANGES))
        return [
            TextContent(
                type="text",
                text=f"Invalid exchange: {exchange}. Valid: {valid_list}",
            )
        ]

    if days < 1 or days > 30:
        return [
            TextContent(
                type="text",
                text=f"Invalid days: {days}. Must be 1-30.",
            )
        ]

    tickers = [t.strip().upper() for t in ticker.split(",")]
    is_multi = len(tickers) > 1
    client = get_fio_client()

    async def fetch_one(t: str) -> tuple[str, list[dict[str, Any]] | None]:
        try:
            data = await client.get_price_history(t, exchange)
            return (t, data)
        except FIONotFoundError:
            return (t, None)

    try:
        results = await asyncio.gather(*[fetch_one(t) for t in tickers])
    except FIOApiError as e:
        logger.exception("FIO API error while fetching price history")
        return [TextContent(type="text", text=f"FIO API error: {e}")]

    histories = []
    not_found = []

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    cutoff_ms = now_ms - (days * MS_PER_DAY)

    for t, data in results:
        if data is None:
            not_found.append(t)
            continue

        # Filter to daily candles within the period
        daily_candles = [
            c
            for c in data
            if c.get("Interval") == "DAY_ONE" and c.get("DateEpochMs", 0) >= cutoff_ms
        ]

        # Sort by date descending (most recent first)
        daily_candles.sort(key=lambda c: c.get("DateEpochMs", 0), reverse=True)

        # Format candles
        formatted_daily = []
        for candle in daily_candles:
            date_ms = candle.get("DateEpochMs", 0)
            date_str = datetime.fromtimestamp(date_ms / 1000, tz=timezone.utc).strftime(
                "%Y-%m-%d"
            )

            formatted_daily.append(
                {
                    "date": date_str,
                    "open": candle.get("Open"),
                    "high": candle.get("High"),
                    "low": candle.get("Low"),
                    "close": candle.get("Close"),
                    "volume": candle.get("Traded", 0),
                }
            )

        stats = _calculate_price_stats(daily_candles)

        history: dict[str, Any] = {
            "ticker": t,
            "exchange": exchange,
            "period_days": days,
            "daily": formatted_daily,
            "summary": {
                "avg_price": stats.get("avg_price"),
                "high": stats.get("high"),
                "low": stats.get("low"),
                "total_volume": stats.get("total_volume"),
                "avg_daily_volume": stats.get("avg_daily_volume"),
                "price_change": stats.get("price_change"),
                "price_change_pct": stats.get("price_change_pct"),
            },
        }

        histories.append(history)

    if not histories and not_found:
        return [
            TextContent(
                type="text",
                text=f"No price history for: {', '.join(not_found)}",
            )
        ]

    # Build result
    if is_multi:
        result: dict[str, Any] = {"histories": histories}
        if not_found:
            result["not_found"] = not_found
    else:
        result = histories[0] if histories else {}
        if not_found:
            result["not_found"] = not_found

    return toon_encode(prettify_names(result))
