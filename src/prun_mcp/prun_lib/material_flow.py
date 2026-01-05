"""Material flow tracking business logic."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

MS_PER_DAY = 24 * 60 * 60 * 1000  # Milliseconds per day


class MaterialFlow(BaseModel):
    """Tracks material inputs and outputs."""

    model_config = ConfigDict(populate_by_name=True)

    ticker: str
    input: float = Field(default=0.0, alias="in")
    output: float = Field(default=0.0, alias="out")

    @property
    def delta(self) -> float:
        """Net material flow (output - input)."""
        return self.output - self.input


class MaterialFlowTracker:
    """Accumulates material flows from multiple sources."""

    def __init__(self) -> None:
        self._flows: dict[str, dict[str, float]] = {}

    def add_input(self, ticker: str, amount: float) -> None:
        """Add material consumption (input).

        Args:
            ticker: Material ticker.
            amount: Amount consumed per day.
        """
        if ticker not in self._flows:
            self._flows[ticker] = {"in": 0.0, "out": 0.0}
        self._flows[ticker]["in"] += amount

    def add_output(self, ticker: str, amount: float) -> None:
        """Add material production (output).

        Args:
            ticker: Material ticker.
            amount: Amount produced per day.
        """
        if ticker not in self._flows:
            self._flows[ticker] = {"in": 0.0, "out": 0.0}
        self._flows[ticker]["out"] += amount

    def add_consumption(self, consumption: dict[str, float]) -> None:
        """Add consumption from a dict of ticker -> amount.

        Args:
            consumption: Dict mapping ticker to daily consumption.
        """
        for ticker, amount in consumption.items():
            self.add_input(ticker, amount)

    def get_flows(self) -> dict[str, dict[str, float]]:
        """Get the raw flow data.

        Returns:
            Dict mapping ticker to {"in": amount, "out": amount}.
        """
        return self._flows.copy()

    def get_all_tickers(self) -> list[str]:
        """Get all material tickers in the flow.

        Returns:
            List of all tickers sorted alphabetically.
        """
        return sorted(self._flows.keys())


def calculate_production_runs_per_day(
    duration_ms: int,
    count: int = 1,
    efficiency: float = 1.0,
) -> float:
    """Calculate production runs per day.

    Args:
        duration_ms: Recipe duration in milliseconds.
        count: Number of production lines.
        efficiency: Efficiency multiplier.

    Returns:
        Number of runs per day. Returns 0 if duration is invalid.
    """
    if duration_ms <= 0:
        return 0.0
    return MS_PER_DAY / duration_ms * count * efficiency


def process_recipe_flow(
    recipe: dict[str, Any],
    count: int,
    efficiency: float,
    tracker: MaterialFlowTracker,
) -> bool:
    """Process a recipe and add its material flow to the tracker.

    Args:
        recipe: Recipe dict with Inputs, Outputs, TimeMs/DurationMs.
        count: Number of production lines running this recipe.
        efficiency: Production efficiency multiplier.
        tracker: MaterialFlowTracker to add flows to.

    Returns:
        True if recipe was processed successfully, False if invalid.
    """
    duration_ms = recipe.get("TimeMs") or recipe.get("DurationMs", 0)
    if duration_ms <= 0:
        return False

    runs_per_day = calculate_production_runs_per_day(duration_ms, count, efficiency)

    # Process inputs
    for inp in recipe.get("Inputs", []):
        ticker = inp.get("Ticker", "")
        amount = inp.get("Amount", 0)
        if ticker and amount > 0:
            daily_amount = runs_per_day * amount
            tracker.add_input(ticker, daily_amount)

    # Process outputs
    for out in recipe.get("Outputs", []):
        ticker = out.get("Ticker", "")
        amount = out.get("Amount", 0)
        if ticker and amount > 0:
            daily_amount = runs_per_day * amount
            tracker.add_output(ticker, daily_amount)

    return True


def calculate_material_values(
    flows: dict[str, dict[str, float]],
    prices: dict[str, dict[str, float | None]],
) -> tuple[list[dict[str, Any]], float, list[str]]:
    """Calculate CIS values for material flows.

    Uses ask price for net inputs (buying) and bid price for net outputs (selling).

    Args:
        flows: Dict mapping ticker to {"in": amount, "out": amount}.
        prices: Dict mapping ticker to {"ask": price, "bid": price}.

    Returns:
        Tuple of (materials_list, total_cis_per_day, missing_prices).
    """
    materials: list[dict[str, Any]] = []
    total_cis = 0.0
    missing: list[str] = []

    for ticker in sorted(flows.keys()):
        flow = flows[ticker]
        in_amount = flow["in"]
        out_amount = flow["out"]
        delta = out_amount - in_amount

        price_data = prices.get(ticker, {"ask": None, "bid": None})
        ask = price_data.get("ask")
        bid = price_data.get("bid")

        cis_per_day: float | None = None
        if delta > 0 and bid is not None:
            # Net output - selling
            cis_per_day = delta * bid
            total_cis += cis_per_day
        elif delta < 0 and ask is not None:
            # Net input - buying (negative value)
            cis_per_day = delta * ask
            total_cis += cis_per_day
        elif delta == 0:
            cis_per_day = 0.0
        else:
            missing.append(ticker)

        materials.append(
            {
                "ticker": ticker,
                "in": round(in_amount, 2),
                "out": round(out_amount, 2),
                "delta": round(delta, 2),
                "cis_per_day": round(cis_per_day, 2)
                if cis_per_day is not None
                else None,
            }
        )

    return materials, total_cis, missing
