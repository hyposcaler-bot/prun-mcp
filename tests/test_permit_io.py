"""Tests for permit_io tool."""

from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest
from toon_format import decode as toon_decode

from prun_mcp.cache import BuildingsCache, RecipesCache, WorkforceCache
from prun_mcp.resources.workforce import HABITATION_CAPACITY
from prun_mcp.tools.permit_io import calculate_permit_io

# Default price for missing tickers
DEFAULT_PRICE: dict[str, float | None] = {"ask": None, "bid": None}


pytestmark = pytest.mark.anyio


# Sample data for tests
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
}

SAMPLE_RECIPES = [
    {
        "BuildingTicker": "FP",
        "RecipeName": "1xGRN 1xALG 1xVEG=>10xRAT",
        "Inputs": [
            {"Ticker": "GRN", "Amount": 1},
            {"Ticker": "ALG", "Amount": 1},
            {"Ticker": "VEG", "Amount": 1},
        ],
        "Outputs": [{"Ticker": "RAT", "Amount": 10}],
        "DurationMs": 21600000,  # 6 hours = 4 runs/day
    },
    {
        "BuildingTicker": "FP",
        "RecipeName": "1xCAF 3xDW=>3xCOF",
        "Inputs": [
            {"Ticker": "CAF", "Amount": 1},
            {"Ticker": "DW", "Amount": 3},
        ],
        "Outputs": [{"Ticker": "COF", "Amount": 3}],
        "DurationMs": 25920000,  # 7.2 hours
    },
]

SAMPLE_WORKFORCE_NEEDS = [
    {
        "WorkforceType": "PIONEER",
        "Needs": [
            {"MaterialTicker": "RAT", "Amount": 4.0},
            {"MaterialTicker": "DW", "Amount": 4.0},
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
    cache.refresh(SAMPLE_RECIPES)
    return cache


def create_workforce_cache(tmp_path: Path) -> WorkforceCache:
    """Create a cache populated with workforce needs."""
    cache = WorkforceCache(cache_dir=tmp_path)
    cache.refresh(SAMPLE_WORKFORCE_NEEDS)
    return cache


def mock_prices() -> dict[str, dict[str, float | None]]:
    """Return mock prices with Ask and Bid."""
    return {
        "RAT": {"ask": 100.0, "bid": 90.0},
        "GRN": {"ask": 50.0, "bid": 45.0},
        "ALG": {"ask": 60.0, "bid": 55.0},
        "VEG": {"ask": 70.0, "bid": 65.0},
        "DW": {"ask": 30.0, "bid": 25.0},
        "CAF": {"ask": 200.0, "bid": 180.0},
        "COF": {"ask": 150.0, "bid": 140.0},
    }


class TestHabitationCapacity:
    """Tests for habitation capacity data."""

    def test_all_single_type_buildings(self) -> None:
        """Single-type buildings should have 100 capacity."""
        for building in ["HB1", "HB2", "HB3", "HB4", "HB5"]:
            cap = HABITATION_CAPACITY[building]
            assert sum(cap.values()) == 100

    def test_all_mixed_type_buildings(self) -> None:
        """Mixed-type buildings should have 150 total capacity."""
        for building in ["HBB", "HBC", "HBM", "HBL"]:
            cap = HABITATION_CAPACITY[building]
            assert sum(cap.values()) == 150


class TestCalculatePermitIoValidation:
    """Tests for input validation."""

    async def test_invalid_exchange(self) -> None:
        """Should reject invalid exchange."""
        result = await calculate_permit_io(
            production=[{"recipe": "test", "count": 1, "efficiency": 1.0}],
            habitation=[],
            exchange="INVALID",
        )
        assert len(result) == 1
        assert "Invalid exchange" in result[0].text

    async def test_empty_production(self) -> None:
        """Should reject empty production list."""
        result = await calculate_permit_io(
            production=[],
            habitation=[],
            exchange="CI1",
        )
        assert len(result) == 1
        assert "No production entries" in result[0].text

    async def test_missing_recipe_field(self) -> None:
        """Should reject production entry without recipe."""
        result = await calculate_permit_io(
            production=[{"count": 1, "efficiency": 1.0}],
            habitation=[],
            exchange="CI1",
        )
        assert len(result) == 1
        assert "missing 'recipe'" in result[0].text

    async def test_missing_count_field(self) -> None:
        """Should reject production entry without count."""
        result = await calculate_permit_io(
            production=[{"recipe": "test", "efficiency": 1.0}],
            habitation=[],
            exchange="CI1",
        )
        assert len(result) == 1
        assert "missing 'count'" in result[0].text

    async def test_missing_efficiency_field(self) -> None:
        """Should reject production entry without efficiency."""
        result = await calculate_permit_io(
            production=[{"recipe": "test", "count": 1}],
            habitation=[],
            exchange="CI1",
        )
        assert len(result) == 1
        assert "missing 'efficiency'" in result[0].text

    async def test_invalid_count(self) -> None:
        """Should reject count < 1."""
        result = await calculate_permit_io(
            production=[{"recipe": "test", "count": 0, "efficiency": 1.0}],
            habitation=[],
            exchange="CI1",
        )
        assert len(result) == 1
        assert "count must be >= 1" in result[0].text

    async def test_invalid_efficiency(self) -> None:
        """Should reject efficiency <= 0."""
        result = await calculate_permit_io(
            production=[{"recipe": "test", "count": 1, "efficiency": 0}],
            habitation=[],
            exchange="CI1",
        )
        assert len(result) == 1
        assert "efficiency must be > 0" in result[0].text

    async def test_invalid_habitation_building(self) -> None:
        """Should reject unknown habitation building."""
        result = await calculate_permit_io(
            production=[{"recipe": "test", "count": 1, "efficiency": 1.0}],
            habitation=[{"building": "INVALID", "count": 1}],
            exchange="CI1",
        )
        assert len(result) == 1
        assert "Unknown habitation building" in result[0].text


class TestCalculatePermitIo:
    """Tests for calculate_permit_io function."""

    async def test_basic_calculation(self, tmp_path: Path) -> None:
        """Should calculate basic I/O correctly."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")
        prices = mock_prices()

        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            return {t: prices.get(t, DEFAULT_PRICE) for t in tickers}

        with (
            patch(
                "prun_mcp.tools.permit_io.get_buildings_cache",
                return_value=buildings_cache,
            ),
            patch(
                "prun_mcp.tools.permit_io.get_recipes_cache", return_value=recipes_cache
            ),
            patch(
                "prun_mcp.tools.permit_io.get_workforce_cache",
                return_value=workforce_cache,
            ),
            patch("prun_mcp.tools.permit_io.fetch_prices", mock_fetch_prices),
        ):
            result = await calculate_permit_io(
                production=[
                    {
                        "recipe": "1xGRN 1xALG 1xVEG=>10xRAT",
                        "count": 1,
                        "efficiency": 1.0,
                    }
                ],
                habitation=[{"building": "HB1", "count": 1}],
                exchange="CI1",
            )

        assert isinstance(result, str)
        decoded = cast(dict[str, Any], toon_decode(result))

        # Verify structure
        assert "materials" in decoded
        assert "workforce" in decoded
        assert "habitation" in decoded
        assert "totals" in decoded

    async def test_habitation_sufficient(self, tmp_path: Path) -> None:
        """Should validate sufficient habitation."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")
        prices = mock_prices()

        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            return {t: prices.get(t, DEFAULT_PRICE) for t in tickers}

        with (
            patch(
                "prun_mcp.tools.permit_io.get_buildings_cache",
                return_value=buildings_cache,
            ),
            patch(
                "prun_mcp.tools.permit_io.get_recipes_cache", return_value=recipes_cache
            ),
            patch(
                "prun_mcp.tools.permit_io.get_workforce_cache",
                return_value=workforce_cache,
            ),
            patch("prun_mcp.tools.permit_io.fetch_prices", mock_fetch_prices),
        ):
            result = await calculate_permit_io(
                production=[
                    {
                        "recipe": "1xGRN 1xALG 1xVEG=>10xRAT",
                        "count": 1,
                        "efficiency": 1.0,
                    }
                ],
                habitation=[{"building": "HB1", "count": 1}],  # 100 pioneers, need 40
                exchange="CI1",
            )

        decoded = cast(dict[str, Any], toon_decode(result))
        assert decoded["habitation"]["sufficient"] is True

    async def test_habitation_insufficient(self, tmp_path: Path) -> None:
        """Should warn about insufficient habitation."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")
        prices = mock_prices()

        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            return {t: prices.get(t, DEFAULT_PRICE) for t in tickers}

        with (
            patch(
                "prun_mcp.tools.permit_io.get_buildings_cache",
                return_value=buildings_cache,
            ),
            patch(
                "prun_mcp.tools.permit_io.get_recipes_cache", return_value=recipes_cache
            ),
            patch(
                "prun_mcp.tools.permit_io.get_workforce_cache",
                return_value=workforce_cache,
            ),
            patch("prun_mcp.tools.permit_io.fetch_prices", mock_fetch_prices),
        ):
            result = await calculate_permit_io(
                production=[
                    {
                        "recipe": "1xGRN 1xALG 1xVEG=>10xRAT",
                        "count": 10,  # 400 pioneers needed
                        "efficiency": 1.0,
                    }
                ],
                habitation=[{"building": "HB1", "count": 1}],  # Only 100 pioneers
                exchange="CI1",
            )

        decoded = cast(dict[str, Any], toon_decode(result))
        assert decoded["habitation"]["sufficient"] is False

    async def test_material_delta_calculation(self, tmp_path: Path) -> None:
        """Should calculate delta correctly (out - in)."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        recipes_cache = create_recipes_cache(tmp_path / "recipes")
        workforce_cache = create_workforce_cache(tmp_path / "workforce")
        prices = mock_prices()

        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            return {t: prices.get(t, DEFAULT_PRICE) for t in tickers}

        with (
            patch(
                "prun_mcp.tools.permit_io.get_buildings_cache",
                return_value=buildings_cache,
            ),
            patch(
                "prun_mcp.tools.permit_io.get_recipes_cache", return_value=recipes_cache
            ),
            patch(
                "prun_mcp.tools.permit_io.get_workforce_cache",
                return_value=workforce_cache,
            ),
            patch("prun_mcp.tools.permit_io.fetch_prices", mock_fetch_prices),
        ):
            result = await calculate_permit_io(
                production=[
                    {
                        "recipe": "1xGRN 1xALG 1xVEG=>10xRAT",
                        "count": 1,
                        "efficiency": 1.0,
                    }
                ],
                habitation=[{"building": "HB1", "count": 1}],
                exchange="CI1",
            )

        decoded = cast(dict[str, Any], toon_decode(result))
        materials: dict[str, Any] = {m["ticker"]: m for m in decoded["materials"]}

        # RAT: 40 out (4 runs * 10), 1.6 in (40 workers * 4/100) = +38.4 delta
        # At 100% efficiency, 1 FP runs 4 times/day producing 40 RAT
        # Workforce consumes 40 * 4 / 100 = 1.6 RAT/day
        rat = materials["RAT"]
        assert rat["out"] == 40.0  # 4 runs * 10 RAT
        assert rat["in"] == 1.6  # 40 pioneers * 4/100
        assert rat["delta"] == 38.4  # out - in

        # GRN: 0 out, 4 in (4 runs * 1) = -4 delta
        grn = materials["GRN"]
        assert grn["out"] == 0
        assert grn["in"] == 4.0
        assert grn["delta"] == -4.0
