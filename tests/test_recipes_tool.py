"""Tests for recipe tools."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import TextContent
from toon_format import decode as toon_decode

from prun_mcp.cache import RecipesCache
from prun_mcp.fio import FIOApiError
from prun_mcp.tools.recipes import (
    get_recipe_info,
    refresh_recipes_cache,
    search_recipes,
)

from tests.conftest import SAMPLE_RECIPES


pytestmark = pytest.mark.anyio


def create_populated_cache(tmp_path: Path) -> RecipesCache:
    """Create a cache populated with sample data."""
    cache = RecipesCache(cache_dir=tmp_path)
    cache.refresh(SAMPLE_RECIPES)
    return cache


class TestGetRecipeInfo:
    """Tests for get_recipe_info tool."""

    async def test_returns_toon_encoded_data(self, tmp_path: Path) -> None:
        """Test successful recipe lookup returns TOON-encoded data."""
        cache = create_populated_cache(tmp_path)

        with patch(
            "prun_mcp.cache.ensure_recipes_cache", AsyncMock(return_value=cache)
        ):
            result = await get_recipe_info("RAT")

        assert isinstance(result, str)

        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        assert "recipes" in decoded  # type: ignore[operator]

        recipes = decoded["recipes"]  # type: ignore[index]
        assert len(recipes) == 2

        # All should be FP recipes producing RAT
        for recipe in recipes:
            assert recipe["BuildingTicker"] == "FP"  # type: ignore[index]

    async def test_lowercase_ticker_converted(self, tmp_path: Path) -> None:
        """Test that lowercase tickers are converted to uppercase."""
        cache = create_populated_cache(tmp_path)

        with patch(
            "prun_mcp.cache.ensure_recipes_cache", AsyncMock(return_value=cache)
        ):
            result = await get_recipe_info("rat")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        recipes = decoded["recipes"]  # type: ignore[index]
        assert len(recipes) == 2

    async def test_multiple_tickers(self, tmp_path: Path) -> None:
        """Test comma-separated tickers returns recipes for all materials."""
        cache = create_populated_cache(tmp_path)

        with patch(
            "prun_mcp.cache.ensure_recipes_cache", AsyncMock(return_value=cache)
        ):
            result = await get_recipe_info("RAT,BSE")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        recipes = decoded["recipes"]  # type: ignore[index]
        # 2 RAT recipes + 1 BSE recipe
        assert len(recipes) == 3

    async def test_multiple_tickers_with_spaces(self, tmp_path: Path) -> None:
        """Test comma-separated tickers with spaces are handled."""
        cache = create_populated_cache(tmp_path)

        with patch(
            "prun_mcp.cache.ensure_recipes_cache", AsyncMock(return_value=cache)
        ):
            result = await get_recipe_info("RAT, BSE")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        recipes = decoded["recipes"]  # type: ignore[index]
        assert len(recipes) == 3

    async def test_partial_match_includes_not_found(self, tmp_path: Path) -> None:
        """Test partial matches return found recipes plus not_found list."""
        cache = create_populated_cache(tmp_path)

        with patch(
            "prun_mcp.cache.ensure_recipes_cache", AsyncMock(return_value=cache)
        ):
            result = await get_recipe_info("RAT,INVALID,BSE")

        assert isinstance(result, str)
        decoded = toon_decode(result)

        # Should have found recipes
        recipes = decoded["recipes"]  # type: ignore[index]
        assert len(recipes) == 3

        # Should have not_found list
        not_found = decoded["not_found"]  # type: ignore[index]
        assert "INVALID" in not_found

    async def test_all_not_found(self, tmp_path: Path) -> None:
        """Test all recipes not found returns error content."""
        cache = create_populated_cache(tmp_path)

        with patch(
            "prun_mcp.cache.ensure_recipes_cache", AsyncMock(return_value=cache)
        ):
            result = await get_recipe_info("INVALID1,INVALID2")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "no recipes found" in result[0].text.lower()
        assert "INVALID1" in result[0].text
        assert "INVALID2" in result[0].text

    async def test_api_error_returns_error_content(self) -> None:
        """Test FIO API error returns error content."""
        mock_ensure = AsyncMock(
            side_effect=FIOApiError("Server error", status_code=500)
        )

        with patch("prun_mcp.cache.ensure_recipes_cache", mock_ensure):
            result = await get_recipe_info("RAT")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text

    async def test_populates_cache_on_miss(self, tmp_path: Path) -> None:
        """Test that cache is populated when invalid (ensure_recipes_cache handles this)."""
        cache = create_populated_cache(tmp_path)

        with patch(
            "prun_mcp.cache.ensure_recipes_cache", AsyncMock(return_value=cache)
        ):
            result = await get_recipe_info("RAT")

        assert isinstance(result, str)


class TestSearchRecipes:
    """Tests for search_recipes tool."""

    async def test_no_filters_returns_all(self, tmp_path: Path) -> None:
        """Test that search_recipes with no filters returns all recipes."""
        cache = create_populated_cache(tmp_path)

        with patch(
            "prun_mcp.cache.ensure_recipes_cache", AsyncMock(return_value=cache)
        ):
            result = await search_recipes()

        assert isinstance(result, str)

        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        assert "recipes" in decoded
        recipes = decoded["recipes"]
        assert len(recipes) == 5

    async def test_filter_by_building(self, tmp_path: Path) -> None:
        """Test filtering by building ticker."""
        from prun_mcp.cache import BuildingsCache

        from tests.conftest import SAMPLE_BUILDINGS

        cache = create_populated_cache(tmp_path)
        buildings_cache = BuildingsCache(cache_dir=tmp_path / "buildings")
        buildings_cache.refresh(SAMPLE_BUILDINGS)

        with (
            patch(
                "prun_mcp.cache.ensure_recipes_cache",
                AsyncMock(return_value=cache),
            ),
            patch(
                "prun_mcp.cache.ensure_buildings_cache",
                AsyncMock(return_value=buildings_cache),
            ),
        ):
            result = await search_recipes(building="PP1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        recipes = decoded["recipes"]
        assert len(recipes) == 2
        for r in recipes:
            assert r["BuildingTicker"] == "PP1"  # type: ignore[index]

    async def test_filter_by_input_tickers(self, tmp_path: Path) -> None:
        """Test filtering by input tickers (AND logic)."""
        cache = create_populated_cache(tmp_path)

        with patch(
            "prun_mcp.cache.ensure_recipes_cache", AsyncMock(return_value=cache)
        ):
            result = await search_recipes(input_tickers=["GRN", "BEA"])

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        recipes = decoded["recipes"]
        assert len(recipes) == 1
        assert recipes[0]["RecipeName"] == "1xGRN 1xBEA 1xNUT=>10xRAT"  # type: ignore[index]

    async def test_filter_by_output_tickers(self, tmp_path: Path) -> None:
        """Test filtering by output tickers."""
        cache = create_populated_cache(tmp_path)

        with patch(
            "prun_mcp.cache.ensure_recipes_cache", AsyncMock(return_value=cache)
        ):
            result = await search_recipes(output_tickers=["RAT"])

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        recipes = decoded["recipes"]
        assert len(recipes) == 2

    async def test_combined_filters(self, tmp_path: Path) -> None:
        """Test combining multiple filters."""
        from prun_mcp.cache import BuildingsCache

        from tests.conftest import SAMPLE_BUILDINGS

        cache = create_populated_cache(tmp_path)
        buildings_cache = BuildingsCache(cache_dir=tmp_path / "buildings")
        buildings_cache.refresh(SAMPLE_BUILDINGS)

        with (
            patch(
                "prun_mcp.cache.ensure_recipes_cache",
                AsyncMock(return_value=cache),
            ),
            patch(
                "prun_mcp.cache.ensure_buildings_cache",
                AsyncMock(return_value=buildings_cache),
            ),
        ):
            result = await search_recipes(
                building="FP", input_tickers=["GRN"], output_tickers=["RAT"]
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        recipes = decoded["recipes"]
        assert len(recipes) == 1

    async def test_populates_cache_on_miss(self, tmp_path: Path) -> None:
        """Test that cache is populated when invalid (ensure_recipes_cache handles this)."""
        cache = create_populated_cache(tmp_path)

        with patch(
            "prun_mcp.cache.ensure_recipes_cache", AsyncMock(return_value=cache)
        ):
            result = await search_recipes()

        assert isinstance(result, str)

    async def test_api_error_returns_error_content(self) -> None:
        """Test FIO API error returns error content."""
        mock_ensure = AsyncMock(
            side_effect=FIOApiError("Server error", status_code=500)
        )

        with patch("prun_mcp.cache.ensure_recipes_cache", mock_ensure):
            result = await search_recipes()

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text

    async def test_invalid_building_returns_error(self, tmp_path: Path) -> None:
        """Test that invalid building ticker returns error."""
        from prun_mcp.cache import BuildingsCache

        from tests.conftest import SAMPLE_BUILDINGS

        # Set up buildings cache with sample data
        buildings_cache = BuildingsCache(cache_dir=tmp_path)
        buildings_cache.refresh(SAMPLE_BUILDINGS)

        with patch(
            "prun_mcp.cache.ensure_buildings_cache",
            AsyncMock(return_value=buildings_cache),
        ):
            result = await search_recipes(building="INVALID")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unknown building ticker" in result[0].text.lower()
        assert "INVALID" in result[0].text


class TestRefreshRecipesCache:
    """Tests for refresh_recipes_cache tool."""

    async def test_refresh_success(self, tmp_path: Path) -> None:
        """Test successful cache refresh."""
        cache = RecipesCache(cache_dir=tmp_path)

        mock_client = AsyncMock()
        mock_client.get_all_recipes.return_value = SAMPLE_RECIPES

        with (
            patch("prun_mcp.cache.get_recipes_cache", return_value=cache),
            patch("prun_mcp.fio.get_fio_client", return_value=mock_client),
        ):
            result = await refresh_recipes_cache()

        assert "refreshed" in result.lower()
        assert "5" in result  # 5 recipes in SAMPLE_RECIPES
        mock_client.get_all_recipes.assert_called_once()

    async def test_refresh_invalidates_first(self, tmp_path: Path) -> None:
        """Test that refresh invalidates cache before fetching."""
        # Pre-populate cache with old data
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(
            [
                {
                    "BuildingTicker": "OLD",
                    "RecipeName": "OLD=>OLD",
                    "Inputs": [],
                    "Outputs": [{"Ticker": "OLD", "Amount": 1}],
                    "TimeMs": 1000,
                }
            ]
        )

        mock_client = AsyncMock()
        mock_client.get_all_recipes.return_value = SAMPLE_RECIPES

        with (
            patch("prun_mcp.cache.get_recipes_cache", return_value=cache),
            patch("prun_mcp.fio.get_fio_client", return_value=mock_client),
        ):
            await refresh_recipes_cache()

        # Cache should now have new data
        assert len(cache.get_recipes_by_output("RAT")) == 2
        assert len(cache.get_recipes_by_output("OLD")) == 0

    async def test_refresh_api_error(self, tmp_path: Path) -> None:
        """Test refresh handles API errors gracefully."""
        cache = RecipesCache(cache_dir=tmp_path)

        mock_client = AsyncMock()
        mock_client.get_all_recipes.side_effect = FIOApiError(
            "Server error", status_code=500
        )

        with (
            patch("prun_mcp.cache.get_recipes_cache", return_value=cache),
            patch("prun_mcp.fio.get_fio_client", return_value=mock_client),
        ):
            result = await refresh_recipes_cache()

        assert "failed" in result.lower()
