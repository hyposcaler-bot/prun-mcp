"""COGM (Cost of Goods Manufactured) calculation business logic."""

from typing import Any

from prun_mcp.models.domain import (
    COGMBreakdown,
    COGMConsumableBreakdown,
    COGMInputBreakdown,
    COGMOutput,
    COGMResult,
    COGMSelfConsumption,
    COGMTotals,
)
from prun_mcp.prun_lib.workforce import (
    WORKFORCE_TYPES,
    WorkforceNeedsProvider,
    get_consumable_tickers,
    get_workforce_from_building,
    normalize_workforce_type,
)

MS_PER_DAY = 24 * 60 * 60 * 1000  # Milliseconds per day


class COGMCalculationError(Exception):
    """Error during COGM calculation."""

    pass


class RecipeNotFoundError(COGMCalculationError):
    """Recipe not found in cache."""

    def __init__(self, recipe_name: str) -> None:
        self.recipe_name = recipe_name
        super().__init__(f"Recipe not found: {recipe_name}")


class BuildingNotFoundError(COGMCalculationError):
    """Building not found in cache."""

    def __init__(self, building_ticker: str) -> None:
        self.building_ticker = building_ticker
        super().__init__(f"Building not found: {building_ticker}")


class InvalidRecipeError(COGMCalculationError):
    """Recipe has invalid data."""

    pass


def calculate_runs_per_day(
    duration_ms: int,
    efficiency: float = 1.0,
    count: int = 1,
) -> float:
    """Calculate production runs per day.

    Args:
        duration_ms: Recipe duration in milliseconds.
        efficiency: Production efficiency multiplier.
        count: Number of production lines.

    Returns:
        Number of production runs per day.

    Raises:
        InvalidRecipeError: If duration is invalid.
    """
    if duration_ms <= 0:
        raise InvalidRecipeError(f"Invalid recipe duration: {duration_ms}")
    return MS_PER_DAY / duration_ms * efficiency * count


def calculate_input_costs(
    inputs: list[dict[str, Any]],
    runs_per_day: float,
    prices: dict[str, dict[str, float | None]],
) -> tuple[list[COGMInputBreakdown], float, list[str]]:
    """Calculate daily input costs.

    Args:
        inputs: Recipe inputs (list of dicts with Ticker and Amount).
        runs_per_day: Production runs per day.
        prices: Dict mapping ticker to {"ask": price, "bid": price}.

    Returns:
        Tuple of (input_breakdown, daily_input_cost, missing_prices).
    """
    breakdown: list[COGMInputBreakdown] = []
    daily_cost = 0.0
    missing: list[str] = []

    for inp in inputs:
        ticker = inp.get("Ticker", "")
        amount = inp.get("Amount", 0)
        daily_amount = runs_per_day * amount
        price = prices.get(ticker, {"ask": None})["ask"]

        if price is None:
            missing.append(ticker)
            breakdown.append(
                COGMInputBreakdown(
                    ticker=ticker,
                    daily_amount=round(daily_amount, 2),
                    price=None,
                    daily_cost=None,
                )
            )
        else:
            item_daily_cost = daily_amount * price
            daily_cost += item_daily_cost
            breakdown.append(
                COGMInputBreakdown(
                    ticker=ticker,
                    daily_amount=round(daily_amount, 2),
                    price=round(price, 2),
                    daily_cost=round(item_daily_cost, 2),
                )
            )

    return breakdown, daily_cost, missing


def calculate_consumable_costs(
    building: dict[str, Any],
    workforce_cache: WorkforceNeedsProvider,
    prices: dict[str, dict[str, float | None]],
    output_tickers: set[str],
    self_consume: bool = False,
) -> tuple[list[COGMConsumableBreakdown], float, dict[str, float], list[str]]:
    """Calculate daily workforce consumable costs.

    Args:
        building: Building dict with workforce type keys.
        workforce_cache: Provider for workforce needs data.
        prices: Dict mapping ticker to {"ask": price, "bid": price}.
        output_tickers: Set of output tickers (for self-consumption).
        self_consume: If True, outputs can satisfy workforce needs.

    Returns:
        Tuple of (breakdown, daily_cost, self_consumed, missing_prices).
    """
    breakdown: list[COGMConsumableBreakdown] = []
    daily_cost = 0.0
    self_consumed: dict[str, float] = {}
    missing: list[str] = []

    for wf_type in WORKFORCE_TYPES:
        worker_count = building.get(wf_type, 0)
        if worker_count <= 0:
            continue

        normalized_type = normalize_workforce_type(wf_type)
        needs = workforce_cache.get_needs(normalized_type)
        if not needs:
            continue

        for need in needs:
            ticker = need.get("MaterialTicker", "")
            amount_per_100 = need.get("Amount", 0)
            daily_amount = (worker_count / 100) * amount_per_100

            is_self_consumed = self_consume and ticker.upper() in output_tickers

            if is_self_consumed:
                self_consumed[ticker] = self_consumed.get(ticker, 0) + daily_amount
                breakdown.append(
                    COGMConsumableBreakdown(
                        ticker=ticker,
                        workforce_type=wf_type,
                        daily_amount=round(daily_amount, 4),
                        price="self",
                        daily_cost=0,
                        self_consumed=True,
                    )
                )
            else:
                price = prices.get(ticker, {"ask": None})["ask"]
                if price is None:
                    if ticker not in missing:
                        missing.append(ticker)
                    breakdown.append(
                        COGMConsumableBreakdown(
                            ticker=ticker,
                            workforce_type=wf_type,
                            daily_amount=round(daily_amount, 4),
                            price=None,
                            daily_cost=None,
                        )
                    )
                else:
                    item_daily_cost = daily_amount * price
                    daily_cost += item_daily_cost
                    breakdown.append(
                        COGMConsumableBreakdown(
                            ticker=ticker,
                            workforce_type=wf_type,
                            daily_amount=round(daily_amount, 4),
                            price=round(price, 2),
                            daily_cost=round(item_daily_cost, 2),
                        )
                    )

    return breakdown, daily_cost, self_consumed, missing


def _calculate_cogm_core(
    recipe_name: str,
    recipe_data: dict[str, Any],
    building: dict[str, Any],
    workforce_cache: WorkforceNeedsProvider,
    prices: dict[str, dict[str, float | None]],
    exchange: str,
    efficiency: float = 1.0,
    self_consume: bool = False,
) -> COGMResult:
    """Core COGM calculation with pre-fetched data (internal use).

    Args:
        recipe_name: Recipe name for display.
        recipe_data: Recipe dict with Inputs, Outputs, TimeMs/DurationMs.
        building: Building dict with workforce counts and ticker.
        workforce_cache: Provider for workforce needs data.
        prices: Dict mapping ticker to {"ask": price, "bid": price}.
        exchange: Exchange code used for pricing.
        efficiency: Production efficiency multiplier.
        self_consume: If True, outputs can satisfy workforce needs.

    Returns:
        COGMResult with complete calculation breakdown.

    Raises:
        InvalidRecipeError: If recipe data is invalid.
    """
    # Calculate daily production rate
    duration_ms = recipe_data.get("TimeMs") or recipe_data.get("DurationMs", 0)
    runs_per_day = calculate_runs_per_day(duration_ms, efficiency)

    # Get outputs
    outputs = recipe_data.get("Outputs", [])
    if not outputs:
        raise InvalidRecipeError("Recipe has no outputs")

    primary_output = outputs[0]
    output_ticker = primary_output.get("Ticker", "")
    output_amount = primary_output.get("Amount", 0)
    daily_output = runs_per_day * output_amount

    output_tickers = {out.get("Ticker", "").upper() for out in outputs}

    # Calculate input costs
    input_breakdown, daily_input_cost, input_missing = calculate_input_costs(
        recipe_data.get("Inputs", []),
        runs_per_day,
        prices,
    )

    # Calculate consumable costs
    consumable_breakdown, daily_consumable_cost, self_consumed, cons_missing = (
        calculate_consumable_costs(
            building,
            workforce_cache,
            prices,
            output_tickers,
            self_consume,
        )
    )

    # Combine missing prices
    missing_prices = input_missing + [m for m in cons_missing if m not in input_missing]

    # Calculate totals
    total_self_consumed = sum(self_consumed.values())
    net_output = daily_output - total_self_consumed
    daily_total_cost = daily_input_cost + daily_consumable_cost
    effective_output = net_output if self_consume else daily_output
    cogm_per_unit = daily_total_cost / effective_output if effective_output > 0 else 0

    building_ticker = building.get("Ticker", recipe_data.get("BuildingTicker", ""))

    # Build result
    result = COGMResult(
        recipe=recipe_name,
        building=building_ticker,
        efficiency=efficiency,
        exchange=exchange,
        self_consume=self_consume,
        output=COGMOutput(
            ticker=output_ticker,
            daily_output=round(daily_output, 2),
        ),
        cogm_per_unit=round(cogm_per_unit, 2),
        breakdown=COGMBreakdown(
            inputs=input_breakdown,
            consumables=consumable_breakdown,
        ),
        totals=COGMTotals(
            daily_input_cost=round(daily_input_cost, 2),
            daily_consumable_cost=round(daily_consumable_cost, 2),
            daily_total_cost=round(daily_total_cost, 2),
        ),
        missing_prices=missing_prices,
    )

    # Add self-consumption info if applicable
    if self_consume and self_consumed:
        result.self_consumption = COGMSelfConsumption(
            consumed={k: round(v, 4) for k, v in self_consumed.items()},
            net_output=round(net_output, 2),
        )

    return result


class InvalidEfficiencyError(COGMCalculationError):
    """Efficiency value is invalid."""

    def __init__(self, efficiency: float) -> None:
        self.efficiency = efficiency
        super().__init__(f"Efficiency must be greater than 0, got: {efficiency}")


async def calculate_cogm(
    recipe_name: str,
    exchange: str,
    efficiency: float = 1.0,
    self_consume: bool = False,
) -> COGMResult:
    """Calculate Cost of Goods Manufactured for a recipe.

    This is the main entry point that handles validation, data fetching,
    and calculation.

    Args:
        recipe_name: Recipe name (e.g., "1xGRN 1xBEA 1xNUT=>10xRAT")
        exchange: Exchange code for pricing (e.g., "CI1")
        efficiency: Production efficiency multiplier (default: 1.0)
        self_consume: If True, use produced output to satisfy workforce needs

    Returns:
        COGMResult with complete calculation breakdown.

    Raises:
        InvalidExchangeError: If exchange code is invalid.
        InvalidEfficiencyError: If efficiency is <= 0.
        RecipeNotFoundError: If recipe is not found in cache.
        BuildingNotFoundError: If building is not found in cache.
        InvalidRecipeError: If recipe data is invalid.
    """
    from prun_mcp.cache import (
        ensure_buildings_cache,
        ensure_recipes_cache,
        ensure_workforce_cache,
    )
    from prun_mcp.prun_lib.exchange import InvalidExchangeError, validate_exchange
    from prun_mcp.utils import fetch_prices

    # Validate inputs
    validated_exchange = validate_exchange(exchange)
    if validated_exchange is None:
        raise InvalidExchangeError("Exchange is required")
    exchange = validated_exchange

    if efficiency <= 0:
        raise InvalidEfficiencyError(efficiency)

    # Load caches
    recipes_cache = await ensure_recipes_cache()
    buildings_cache = await ensure_buildings_cache()
    workforce_cache = await ensure_workforce_cache()

    # Look up recipe
    recipe_data = recipes_cache.get_recipe_by_name(recipe_name)
    if not recipe_data:
        raise RecipeNotFoundError(recipe_name)

    # Get building info
    building_ticker = recipe_data.get("BuildingTicker", "")
    building = buildings_cache.get_building(building_ticker)
    if not building:
        raise BuildingNotFoundError(building_ticker)

    # Collect tickers for price fetching
    input_tickers = [inp.get("Ticker", "") for inp in recipe_data.get("Inputs", [])]
    workforce_counts = get_workforce_from_building(building)
    consumable_tickers = get_consumable_tickers(workforce_counts, workforce_cache)
    all_tickers = list(set(input_tickers) | consumable_tickers)

    # Fetch prices
    prices = await fetch_prices(all_tickers, exchange)

    # Calculate using core logic
    return _calculate_cogm_core(
        recipe_name=recipe_name,
        recipe_data=recipe_data,
        building=building,
        workforce_cache=workforce_cache,
        prices=prices,
        exchange=exchange,
        efficiency=efficiency,
        self_consume=self_consume,
    )
