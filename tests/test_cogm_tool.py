"""Tests for COGM (Cost of Goods Manufactured) tool."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import TextContent
from toon_format import decode as toon_decode

from prun_mcp.cache import BuildingsCache, RecipesCache, WorkforceCache
from prun_mcp.fio import FIOApiError
from prun_mcp.tools.cogm import calculate_cogm


pytestmark = pytest.mark.anyio


# Sample data for COGM tests
SAMPLE_FP_BUILDING = {
    "BuildingId": "fp-building-id",
    "Name": "foodProcessor",
    "Ticker": "FP",
    "Expertise": "FOOD_INDUSTRIES",
    "Pioneers": 40,
    "Settlers": 0,
    "Technicians": 0,
    "Engineers": 0,
    "Scientists": 0,
    "AreaCost": 12,
    "BuildingCosts": [
        {"CommodityTicker": "BSE", "Amount": 3},
        {"CommodityTicker": "BBH", "Amount": 3},
        {"CommodityTicker": "BDE", "Amount": 3},
    ],
}

SAMPLE_COGM_RECIPES = [
    {
        "BuildingTicker": "FP",
        "RecipeName": "1xGRN 1xBEA 1xNUT=>10xRAT",
        "Inputs": [
            {"Ticker": "GRN", "Amount": 1},
            {"Ticker": "BEA", "Amount": 1},
            {"Ticker": "NUT", "Amount": 1},
        ],
        "Outputs": [{"Ticker": "RAT", "Amount": 10}],
        "DurationMs": 21600000,  # 6 hours
    },
]

SAMPLE_WORKFORCE_NEEDS = [
    {
        "WorkforceType": "PIONEER",
        "Needs": [
            {"MaterialTicker": "RAT", "Amount": 4.0},
            {"MaterialTicker": "DW", "Amount": 4.0},
            {"MaterialTicker": "OVE", "Amount": 0.5},
        ],
    },
    {
        "WorkforceType": "SETTLER",
        "Needs": [
            {"MaterialTicker": "RAT", "Amount": 6.0},
            {"MaterialTicker": "DW", "Amount": 5.0},
        ],
    },
]


def create_buildings_cache(tmp_path: Path) -> BuildingsCache:
    """Create a cache populated with FP building."""
    cache = BuildingsCache(cache_dir=tmp_path)
    cache.refresh([SAMPLE_FP_BUILDING])
    return cache


def create_recipes_cache(tmp_path: Path) -> RecipesCache:
    """Create a cache populated with sample recipes."""
    cache = RecipesCache(cache_dir=tmp_path)
    cache.refresh(SAMPLE_COGM_RECIPES)
    return cache


def create_workforce_cache(tmp_path: Path) -> WorkforceCache:
    """Create a cache populated with workforce needs."""
    cache = WorkforceCache(cache_dir=tmp_path)
    cache.refresh(SAMPLE_WORKFORCE_NEEDS)
    return cache


def mock_prices() -> dict[str, float]:
    """Return mock prices for testing."""
    return {
        "GRN": 45.0,
        "BEA": 55.0,
        "NUT": 60.0,
        "RAT": 175.0,
        "DW": 15.0,
        "OVE": 250.0,
    }


class TestCalculateCogm:
    """Tests for calculate_cogm tool."""

    async def test_basic_cogm_calculation(self, tmp_path: Path) -> None:
        """Test basic COGM calculation returns valid result."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")
        prices = mock_prices()

        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            return {t: {"ask": prices.get(t), "bid": prices.get(t)} for t in tickers}

        with (
            patch(
                "prun_mcp.tools.cogm.ensure_buildings_cache",
                AsyncMock(return_value=buildings_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_recipes_cache",
                AsyncMock(return_value=recipes_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_workforce_cache",
                AsyncMock(return_value=workforce_cache),
            ),
            patch("prun_mcp.tools.cogm.fetch_prices", mock_fetch_prices),
        ):
            result = await calculate_cogm(
                recipe="1xGRN 1xBEA 1xNUT=>10xRAT",
                exchange="CI1",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, dict)

        # Verify structure
        assert "recipe" in decoded  # type: ignore[operator]
        assert "building" in decoded  # type: ignore[operator]
        assert "cogm_per_unit" in decoded  # type: ignore[operator]
        assert "output" in decoded  # type: ignore[operator]
        assert "breakdown" in decoded  # type: ignore[operator]
        assert "totals" in decoded  # type: ignore[operator]

        # Verify basic values
        assert decoded["recipe"] == "1xGRN 1xBEA 1xNUT=>10xRAT"  # type: ignore[index]
        assert decoded["building"] == "FP"  # type: ignore[index]
        assert decoded["efficiency"] == 1.0  # type: ignore[index]
        assert decoded["exchange"] == "CI1"  # type: ignore[index]

        # COGM should be positive
        assert decoded["cogm_per_unit"] > 0  # type: ignore[index]

    async def test_efficiency_bonus(self, tmp_path: Path) -> None:
        """Test COGM calculation with efficiency bonus."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")
        prices = mock_prices()

        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            return {t: {"ask": prices.get(t), "bid": prices.get(t)} for t in tickers}

        with (
            patch(
                "prun_mcp.tools.cogm.ensure_buildings_cache",
                AsyncMock(return_value=buildings_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_recipes_cache",
                AsyncMock(return_value=recipes_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_workforce_cache",
                AsyncMock(return_value=workforce_cache),
            ),
            patch("prun_mcp.tools.cogm.fetch_prices", mock_fetch_prices),
        ):
            result = await calculate_cogm(
                recipe="1xGRN 1xBEA 1xNUT=>10xRAT",
                exchange="CI1",
                efficiency=1.33,
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        # With 133% efficiency, output should be higher
        assert decoded["efficiency"] == 1.33  # type: ignore[index]
        output = decoded["output"]  # type: ignore[index]
        # 4 runs/day * 1.33 efficiency * 10 RAT = 53.2 RAT/day
        assert output["DailyOutput"] > 40.0  # Base is 40  # type: ignore[index]

    async def test_invalid_exchange(self, tmp_path: Path) -> None:
        """Test COGM calculation with invalid exchange."""
        result = await calculate_cogm(
            recipe="1xGRN 1xBEA 1xNUT=>10xRAT",
            exchange="INVALID",
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Invalid exchange" in result[0].text
        assert "AI1" in result[0].text  # Shows valid exchanges

    async def test_recipe_not_found(self, tmp_path: Path) -> None:
        """Test COGM calculation with missing recipe."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")

        with (
            patch(
                "prun_mcp.tools.cogm.ensure_buildings_cache",
                AsyncMock(return_value=buildings_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_recipes_cache",
                AsyncMock(return_value=recipes_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_workforce_cache",
                AsyncMock(return_value=workforce_cache),
            ),
        ):
            result = await calculate_cogm(
                recipe="NONEXISTENT=>RECIPE",
                exchange="CI1",
            )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Recipe not found" in result[0].text

    async def test_invalid_efficiency(self, tmp_path: Path) -> None:
        """Test COGM calculation with invalid efficiency."""
        result = await calculate_cogm(
            recipe="1xGRN 1xBEA 1xNUT=>10xRAT",
            exchange="CI1",
            efficiency=0,
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "efficiency" in result[0].text

    async def test_api_error(self, tmp_path: Path) -> None:
        """Test COGM calculation handles API errors gracefully."""
        mock_ensure = AsyncMock(
            side_effect=FIOApiError("Server error", status_code=500)
        )

        with patch("prun_mcp.tools.cogm.ensure_buildings_cache", mock_ensure):
            result = await calculate_cogm(
                recipe="1xGRN 1xBEA 1xNUT=>10xRAT",
                exchange="CI1",
            )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text

    async def test_missing_prices_reported(self, tmp_path: Path) -> None:
        """Test that missing prices are reported in result."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")

        # Only return some prices
        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            prices_data: dict[str, dict[str, float | None]] = {
                "GRN": {"ask": 45.0, "bid": 45.0},
                "BEA": {"ask": None, "bid": None},  # Missing price
                "NUT": {"ask": 60.0, "bid": 60.0},
                "RAT": {"ask": 175.0, "bid": 175.0},
                "DW": {"ask": None, "bid": None},  # Missing price
                "OVE": {"ask": 250.0, "bid": 250.0},
            }
            return {t: prices_data.get(t, {"ask": None, "bid": None}) for t in tickers}

        with (
            patch(
                "prun_mcp.tools.cogm.ensure_buildings_cache",
                AsyncMock(return_value=buildings_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_recipes_cache",
                AsyncMock(return_value=recipes_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_workforce_cache",
                AsyncMock(return_value=workforce_cache),
            ),
            patch("prun_mcp.tools.cogm.fetch_prices", mock_fetch_prices),
        ):
            result = await calculate_cogm(
                recipe="1xGRN 1xBEA 1xNUT=>10xRAT",
                exchange="CI1",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        # Should have missing_prices list
        assert "missing_prices" in decoded  # type: ignore[operator]
        missing = decoded["missing_prices"]  # type: ignore[index]
        assert "BEA" in missing
        assert "DW" in missing

    async def test_breakdown_structure(self, tmp_path: Path) -> None:
        """Test that breakdown has correct structure."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")
        prices = mock_prices()

        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            return {t: {"ask": prices.get(t), "bid": prices.get(t)} for t in tickers}

        with (
            patch(
                "prun_mcp.tools.cogm.ensure_buildings_cache",
                AsyncMock(return_value=buildings_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_recipes_cache",
                AsyncMock(return_value=recipes_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_workforce_cache",
                AsyncMock(return_value=workforce_cache),
            ),
            patch("prun_mcp.tools.cogm.fetch_prices", mock_fetch_prices),
        ):
            result = await calculate_cogm(
                recipe="1xGRN 1xBEA 1xNUT=>10xRAT",
                exchange="CI1",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        breakdown = decoded["breakdown"]  # type: ignore[index]
        assert "inputs" in breakdown  # type: ignore[operator]
        assert "consumables" in breakdown  # type: ignore[operator]

        # Check inputs structure
        inputs = breakdown["inputs"]  # type: ignore[index]
        assert len(inputs) == 3  # GRN, BEA, NUT
        for inp in inputs:  # type: ignore[union-attr]
            assert "Ticker" in inp
            assert "DailyAmount" in inp
            assert "Price" in inp
            assert "DailyCost" in inp

        # Check consumables structure
        consumables = breakdown["consumables"]  # type: ignore[index]
        assert len(consumables) > 0  # Should have RAT, DW, OVE for Pioneers
        for cons in consumables:  # type: ignore[union-attr]
            assert "Ticker" in cons
            assert "WorkforceType" in cons
            assert "DailyAmount" in cons

        # Check totals
        totals = decoded["totals"]  # type: ignore[index]
        assert "daily_input_cost" in totals  # type: ignore[operator]
        assert "daily_consumable_cost" in totals  # type: ignore[operator]
        assert "daily_total_cost" in totals  # type: ignore[operator]
        total_cost = totals["daily_total_cost"]  # type: ignore[index]
        input_cost = totals["daily_input_cost"]  # type: ignore[index]
        consumable_cost = totals["daily_consumable_cost"]  # type: ignore[index]
        assert total_cost == input_cost + consumable_cost

    async def test_self_consume_reduces_cost(self, tmp_path: Path) -> None:
        """Test that self_consume=True reduces consumable cost."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")
        prices = mock_prices()

        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            return {t: {"ask": prices.get(t), "bid": prices.get(t)} for t in tickers}

        with (
            patch(
                "prun_mcp.tools.cogm.ensure_buildings_cache",
                AsyncMock(return_value=buildings_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_recipes_cache",
                AsyncMock(return_value=recipes_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_workforce_cache",
                AsyncMock(return_value=workforce_cache),
            ),
            patch("prun_mcp.tools.cogm.fetch_prices", mock_fetch_prices),
        ):
            # Without self-consume
            result_normal = await calculate_cogm(
                recipe="1xGRN 1xBEA 1xNUT=>10xRAT",
                exchange="CI1",
                self_consume=False,
            )
            # With self-consume
            result_self = await calculate_cogm(
                recipe="1xGRN 1xBEA 1xNUT=>10xRAT",
                exchange="CI1",
                self_consume=True,
            )

        assert isinstance(result_normal, str)
        assert isinstance(result_self, str)

        decoded_normal = toon_decode(result_normal)
        decoded_self = toon_decode(result_self)

        # Self-consume should have lower consumable cost (RAT not purchased)
        normal_consumable = decoded_normal["totals"]["daily_consumable_cost"]  # type: ignore[index]
        self_consumable = decoded_self["totals"]["daily_consumable_cost"]  # type: ignore[index]
        assert self_consumable < normal_consumable

        # Self-consume result should have self_consumption section
        assert "self_consumption" in decoded_self  # type: ignore[operator]
        assert decoded_self["self_consume"] is True  # type: ignore[index]

    async def test_self_consume_net_output(self, tmp_path: Path) -> None:
        """Test that self_consume calculates net output correctly."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")
        prices = mock_prices()

        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            return {t: {"ask": prices.get(t), "bid": prices.get(t)} for t in tickers}

        with (
            patch(
                "prun_mcp.tools.cogm.ensure_buildings_cache",
                AsyncMock(return_value=buildings_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_recipes_cache",
                AsyncMock(return_value=recipes_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_workforce_cache",
                AsyncMock(return_value=workforce_cache),
            ),
            patch("prun_mcp.tools.cogm.fetch_prices", mock_fetch_prices),
        ):
            result = await calculate_cogm(
                recipe="1xGRN 1xBEA 1xNUT=>10xRAT",
                exchange="CI1",
                self_consume=True,
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        # Check self_consumption section exists
        self_consumption = decoded["self_consumption"]  # type: ignore[index]
        assert "consumed" in self_consumption  # type: ignore[operator]
        assert "net_output" in self_consumption  # type: ignore[operator]

        # RAT should be in consumed
        consumed = self_consumption["consumed"]  # type: ignore[index]
        assert "RAT" in consumed  # type: ignore[operator]

        # Net output = gross output - consumed RAT
        gross_output = decoded["output"]["DailyOutput"]  # type: ignore[index]
        net_output = self_consumption["net_output"]  # type: ignore[index]
        consumed_rat = consumed["RAT"]  # type: ignore[index]
        assert net_output == gross_output - consumed_rat  # type: ignore[operator]

    async def test_self_consume_cogm_calculation(self, tmp_path: Path) -> None:
        """Test that COGM uses net output when self_consume is True."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")
        prices = mock_prices()

        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            return {t: {"ask": prices.get(t), "bid": prices.get(t)} for t in tickers}

        with (
            patch(
                "prun_mcp.tools.cogm.ensure_buildings_cache",
                AsyncMock(return_value=buildings_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_recipes_cache",
                AsyncMock(return_value=recipes_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_workforce_cache",
                AsyncMock(return_value=workforce_cache),
            ),
            patch("prun_mcp.tools.cogm.fetch_prices", mock_fetch_prices),
        ):
            result = await calculate_cogm(
                recipe="1xGRN 1xBEA 1xNUT=>10xRAT",
                exchange="CI1",
                self_consume=True,
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        # Verify COGM = total_cost / net_output
        total_cost = decoded["totals"]["daily_total_cost"]  # type: ignore[index]
        net_output = decoded["self_consumption"]["net_output"]  # type: ignore[index]
        expected_cogm = round(total_cost / net_output, 2)  # type: ignore[operator]
        assert decoded["cogm_per_unit"] == expected_cogm  # type: ignore[index]

    async def test_self_consume_marks_consumables(self, tmp_path: Path) -> None:
        """Test that self-consumed consumables are marked in breakdown."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")
        prices = mock_prices()

        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            return {t: {"ask": prices.get(t), "bid": prices.get(t)} for t in tickers}

        with (
            patch(
                "prun_mcp.tools.cogm.ensure_buildings_cache",
                AsyncMock(return_value=buildings_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_recipes_cache",
                AsyncMock(return_value=recipes_cache),
            ),
            patch(
                "prun_mcp.tools.cogm.ensure_workforce_cache",
                AsyncMock(return_value=workforce_cache),
            ),
            patch("prun_mcp.tools.cogm.fetch_prices", mock_fetch_prices),
        ):
            result = await calculate_cogm(
                recipe="1xGRN 1xBEA 1xNUT=>10xRAT",
                exchange="CI1",
                self_consume=True,
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        consumables = decoded["breakdown"]["consumables"]  # type: ignore[index]
        rat_consumable = next(
            (c for c in consumables if c["Ticker"] == "RAT"),  # type: ignore[index]
            None,
        )
        assert rat_consumable is not None
        assert rat_consumable["SelfConsumed"] is True  # type: ignore[index]
        assert rat_consumable["Price"] == "self"  # type: ignore[index]
        assert rat_consumable["DailyCost"] == 0  # type: ignore[index]
