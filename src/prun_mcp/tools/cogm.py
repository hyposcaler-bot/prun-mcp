"""COGM (Cost of Goods Manufactured) calculation tool."""

import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import (
    ensure_buildings_cache,
    ensure_recipes_cache,
    ensure_workforce_cache,
)
from prun_mcp.fio import FIOApiError
from prun_mcp.prun_lib import InvalidExchangeError, validate_exchange
from prun_mcp.resources.workforce import WORKFORCE_TYPES
from prun_mcp.utils import fetch_prices, prettify_names

logger = logging.getLogger(__name__)

MS_PER_DAY = 24 * 60 * 60 * 1000  # Milliseconds per day


@mcp.tool()
async def calculate_cogm(
    recipe: str,
    exchange: str,
    efficiency: float = 1.0,
    self_consume: bool = False,
) -> str | list[TextContent]:
    """Calculate Cost of Goods Manufactured for a recipe.

    Args:
        recipe: Recipe name (e.g., "1xGRN 1xBEA 1xNUT=>10xRAT")
        exchange: Exchange code for pricing (e.g., "CI1").
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.
        efficiency: Production efficiency multiplier (default: 1.0 = 100%)
        self_consume: If True, use produced output to satisfy workforce needs.

    Returns:
        TOON-encoded COGM breakdown including cogm_per_unit, costs, and output.
    """
    try:
        validated_exchange = validate_exchange(exchange)
    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]

    if validated_exchange is None:
        return [TextContent(type="text", text="Exchange is required")]
    exchange = validated_exchange

    if efficiency <= 0:
        return [TextContent(type="text", text="efficiency must be greater than 0")]

    try:
        recipes_cache = await ensure_recipes_cache()
        buildings_cache = await ensure_buildings_cache()
        workforce_cache = await ensure_workforce_cache()

        # Look up recipe
        recipe_data = recipes_cache.get_recipe_by_name(recipe)
        if not recipe_data:
            return [TextContent(type="text", text=f"Recipe not found: {recipe}")]

        # Get building info
        building_ticker = recipe_data.get("BuildingTicker", "")
        building = buildings_cache.get_building(building_ticker)
        if not building:
            return [
                TextContent(type="text", text=f"Building not found: {building_ticker}")
            ]

        # Calculate daily production rate
        duration_ms = recipe_data.get("TimeMs") or recipe_data.get("DurationMs", 0)
        if duration_ms <= 0:
            return [
                TextContent(type="text", text=f"Invalid recipe duration: {duration_ms}")
            ]

        runs_per_day = MS_PER_DAY / duration_ms * efficiency

        outputs = recipe_data.get("Outputs", [])
        if not outputs:
            return [TextContent(type="text", text="Recipe has no outputs")]

        primary_output = outputs[0]
        output_ticker = primary_output.get("Ticker", "")
        output_amount = primary_output.get("Amount", 0)
        daily_output = runs_per_day * output_amount

        output_tickers = {out.get("Ticker", "").upper() for out in outputs}
        self_consumed: dict[str, float] = {}

        input_tickers = [inp.get("Ticker", "") for inp in recipe_data.get("Inputs", [])]

        # Get workforce consumable tickers
        consumable_tickers: set[str] = set()
        for wf_type in WORKFORCE_TYPES:
            worker_count = building.get(wf_type, 0)
            if worker_count > 0:
                wf_type_upper = wf_type.upper()
                if wf_type_upper.endswith("S"):
                    wf_type_upper = wf_type_upper[:-1]
                needs = workforce_cache.get_needs(wf_type_upper)
                if needs:
                    for need in needs:
                        ticker = need.get("MaterialTicker", "")
                        if ticker:
                            consumable_tickers.add(ticker)

        all_tickers = list(set(input_tickers) | consumable_tickers)
        prices = await fetch_prices(all_tickers, exchange)

        # Calculate daily input costs
        input_breakdown: list[dict[str, Any]] = []
        daily_input_cost = 0.0
        missing_prices: list[str] = []

        for inp in recipe_data.get("Inputs", []):
            ticker = inp.get("Ticker", "")
            amount = inp.get("Amount", 0)
            daily_amount = runs_per_day * amount
            price = prices.get(ticker, {"ask": None})["ask"]

            if price is None:
                missing_prices.append(ticker)
                input_breakdown.append(
                    {
                        "Ticker": ticker,
                        "DailyAmount": round(daily_amount, 2),
                        "Price": None,
                        "DailyCost": None,
                    }
                )
            else:
                daily_cost = daily_amount * price
                daily_input_cost += daily_cost
                input_breakdown.append(
                    {
                        "Ticker": ticker,
                        "DailyAmount": round(daily_amount, 2),
                        "Price": round(price, 2),
                        "DailyCost": round(daily_cost, 2),
                    }
                )

        # Calculate daily consumable costs
        consumable_breakdown: list[dict[str, Any]] = []
        daily_consumable_cost = 0.0

        for wf_type in WORKFORCE_TYPES:
            worker_count = building.get(wf_type, 0)
            if worker_count <= 0:
                continue

            wf_type_upper = wf_type.upper()
            if wf_type_upper.endswith("S"):
                wf_type_upper = wf_type_upper[:-1]
            needs = workforce_cache.get_needs(wf_type_upper)
            if not needs:
                continue

            for need in needs:
                ticker = need.get("MaterialTicker", "")
                amount_per_100 = need.get("Amount", 0)
                daily_amount = (worker_count / 100) * amount_per_100

                is_self_consumed = self_consume and ticker.upper() in output_tickers

                if is_self_consumed:
                    self_consumed[ticker] = self_consumed.get(ticker, 0) + daily_amount
                    consumable_breakdown.append(
                        {
                            "Ticker": ticker,
                            "WorkforceType": wf_type,
                            "DailyAmount": round(daily_amount, 4),
                            "Price": "self",
                            "DailyCost": 0,
                            "SelfConsumed": True,
                        }
                    )
                else:
                    price = prices.get(ticker, {"ask": None})["ask"]
                    if price is None:
                        if ticker not in missing_prices:
                            missing_prices.append(ticker)
                        consumable_breakdown.append(
                            {
                                "Ticker": ticker,
                                "WorkforceType": wf_type,
                                "DailyAmount": round(daily_amount, 4),
                                "Price": None,
                                "DailyCost": None,
                            }
                        )
                    else:
                        daily_cost = daily_amount * price
                        daily_consumable_cost += daily_cost
                        consumable_breakdown.append(
                            {
                                "Ticker": ticker,
                                "WorkforceType": wf_type,
                                "DailyAmount": round(daily_amount, 4),
                                "Price": round(price, 2),
                                "DailyCost": round(daily_cost, 2),
                            }
                        )

        total_self_consumed = sum(self_consumed.values())
        net_output = daily_output - total_self_consumed
        daily_total_cost = daily_input_cost + daily_consumable_cost
        effective_output = net_output if self_consume else daily_output
        cogm_per_unit = (
            daily_total_cost / effective_output if effective_output > 0 else 0
        )

        result: dict[str, Any] = {
            "recipe": recipe,
            "building": building_ticker,
            "efficiency": efficiency,
            "exchange": exchange,
            "self_consume": self_consume,
            "output": {
                "Ticker": output_ticker,
                "DailyOutput": round(daily_output, 2),
            },
            "cogm_per_unit": round(cogm_per_unit, 2),
            "breakdown": {
                "inputs": input_breakdown,
                "consumables": consumable_breakdown,
            },
            "totals": {
                "daily_input_cost": round(daily_input_cost, 2),
                "daily_consumable_cost": round(daily_consumable_cost, 2),
                "daily_total_cost": round(daily_total_cost, 2),
            },
        }

        if self_consume and self_consumed:
            result["self_consumption"] = {
                "consumed": {k: round(v, 4) for k, v in self_consumed.items()},
                "net_output": round(net_output, 2),
            }

        if missing_prices:
            result["missing_prices"] = missing_prices

        return toon_encode(prettify_names(result))

    except FIOApiError as e:
        logger.exception("FIO API error while calculating COGM")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
