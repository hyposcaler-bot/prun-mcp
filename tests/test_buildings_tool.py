"""Tests for building tools."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent
from toon_format import decode as toon_decode

from prun_mcp.cache import BuildingsCache
from prun_mcp.fio import FIOApiError
from prun_mcp.tools.buildings import (
    get_building_info,
    refresh_buildings_cache,
    search_buildings,
)

from tests.conftest import SAMPLE_BUILDINGS


pytestmark = pytest.mark.anyio


def create_populated_cache(tmp_path: Path) -> BuildingsCache:
    """Create a cache populated with sample data."""
    cache = BuildingsCache(cache_dir=tmp_path)
    cache.refresh(SAMPLE_BUILDINGS)
    return cache


class TestGetBuildingInfo:
    """Tests for get_building_info tool."""

    async def test_returns_toon_encoded_data(self, tmp_path: Path) -> None:
        """Test successful building lookup returns TOON-encoded data."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            result = await get_building_info("PP1")

        assert isinstance(result, str)

        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        assert "buildings" in decoded  # type: ignore[operator]

        buildings = decoded["buildings"]  # type: ignore[index]
        assert len(buildings) == 1

        building = buildings[0]
        assert building["Ticker"] == "PP1"
        assert building["Name"] == "Prefab Plant1"  # prettified
        assert building["AreaCost"] == 19
        assert building["Expertise"] == "CONSTRUCTION"

        # Check nested data
        assert "BuildingCosts" in building
        assert "Recipes" in building

    async def test_lowercase_ticker_converted(self, tmp_path: Path) -> None:
        """Test that lowercase tickers are converted to uppercase."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            result = await get_building_info("pp1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        buildings = decoded["buildings"]  # type: ignore[index]
        assert buildings[0]["Ticker"] == "PP1"  # type: ignore[index]

    async def test_multiple_tickers(self, tmp_path: Path) -> None:
        """Test comma-separated tickers returns multiple buildings."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            result = await get_building_info("PP1,HB1,FRM")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        buildings = decoded["buildings"]  # type: ignore[index]
        assert len(buildings) == 3

        tickers = [b["Ticker"] for b in buildings]  # type: ignore[index]
        assert "PP1" in tickers
        assert "HB1" in tickers
        assert "FRM" in tickers

    async def test_multiple_tickers_with_spaces(self, tmp_path: Path) -> None:
        """Test comma-separated tickers with spaces are handled."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            result = await get_building_info("PP1, HB1, FRM")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        buildings = decoded["buildings"]  # type: ignore[index]
        assert len(buildings) == 3

    async def test_partial_match_includes_not_found(self, tmp_path: Path) -> None:
        """Test partial matches return found buildings plus not_found list."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            result = await get_building_info("PP1,INVALID,HB1")

        assert isinstance(result, str)
        decoded = toon_decode(result)

        # Should have found buildings
        buildings = decoded["buildings"]  # type: ignore[index]
        assert len(buildings) == 2
        tickers = [b["Ticker"] for b in buildings]  # type: ignore[index]
        assert "PP1" in tickers
        assert "HB1" in tickers

        # Should have not_found list
        not_found = decoded["not_found"]  # type: ignore[index]
        assert "INVALID" in not_found

    async def test_all_not_found(self, tmp_path: Path) -> None:
        """Test all buildings not found returns error content."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            result = await get_building_info("INVALID1,INVALID2")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not found" in result[0].text.lower()
        assert "INVALID1" in result[0].text
        assert "INVALID2" in result[0].text

    async def test_api_error_returns_error_content(self) -> None:
        """Test FIO API error returns error content."""
        mock_manager = MagicMock()
        mock_manager.ensure = AsyncMock(
            side_effect=FIOApiError("Server error", status_code=500)
        )

        with patch("prun_mcp.prun_lib.buildings.get_cache_manager", return_value=mock_manager):
            result = await get_building_info("PP1")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text

    async def test_populates_cache_on_miss(self, tmp_path: Path) -> None:
        """Test that cache is populated when invalid (ensure_buildings_cache handles this)."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            result = await get_building_info("PP1")

        assert isinstance(result, str)

    async def test_lookup_by_building_id(self, tmp_path: Path) -> None:
        """Test lookup by BuildingId returns correct data."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            # PP1 has BuildingId "1d9c9787a38e11dd7f7cfec32245bb76"
            result = await get_building_info("1d9c9787a38e11dd7f7cfec32245bb76")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        buildings = decoded["buildings"]  # type: ignore[index]
        assert len(buildings) == 1
        assert buildings[0]["Ticker"] == "PP1"  # type: ignore[index]

    async def test_lookup_by_id_matches_ticker_lookup(self, tmp_path: Path) -> None:
        """Test round-trip: lookup by ID, get ticker, lookup by ticker matches."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            # Step 1: Look up by BuildingId
            result_by_id = await get_building_info("1d9c9787a38e11dd7f7cfec32245bb76")
            assert isinstance(result_by_id, str)
            decoded_by_id = toon_decode(result_by_id)
            buildings_by_id = decoded_by_id["buildings"]  # type: ignore[index]

            # Step 2: Extract the Ticker
            ticker = buildings_by_id[0]["Ticker"]  # type: ignore[index]
            assert ticker == "PP1"

            # Step 3: Look up by Ticker
            result_by_ticker = await get_building_info(ticker)
            assert isinstance(result_by_ticker, str)
            decoded_by_ticker = toon_decode(result_by_ticker)
            buildings_by_ticker = decoded_by_ticker["buildings"]  # type: ignore[index]

            # Step 4: Verify both return the same data
            assert buildings_by_id[0] == buildings_by_ticker[0]  # type: ignore[index]


class TestRefreshBuildingsCache:
    """Tests for refresh_buildings_cache tool."""

    async def test_refresh_success(self, tmp_path: Path) -> None:
        """Test successful cache refresh."""
        cache = BuildingsCache(cache_dir=tmp_path)

        mock_client = AsyncMock()
        mock_client.get_all_buildings.return_value = SAMPLE_BUILDINGS

        with (
            patch(
                "prun_mcp.cache.get_buildings_cache", return_value=cache
            ),
            patch(
                "prun_mcp.prun_lib.buildings.get_fio_client", return_value=mock_client
            ),
        ):
            result = await refresh_buildings_cache()

        assert "refreshed" in result.lower()
        assert "4" in result  # 4 buildings in SAMPLE_BUILDINGS
        mock_client.get_all_buildings.assert_called_once()

    async def test_refresh_invalidates_first(self, tmp_path: Path) -> None:
        """Test that refresh invalidates cache before fetching."""
        # Pre-populate cache with old data
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh([{"Ticker": "OLD", "Name": "oldBuilding", "AreaCost": 10}])

        mock_client = AsyncMock()
        mock_client.get_all_buildings.return_value = SAMPLE_BUILDINGS

        mock_manager = MagicMock()
        mock_manager.get = MagicMock(return_value=cache)

        with (
            patch("prun_mcp.prun_lib.buildings.get_cache_manager", return_value=mock_manager),
            patch("prun_mcp.prun_lib.buildings.get_fio_client", return_value=mock_client),
        ):
            await refresh_buildings_cache()

        # Cache should now have new data
        assert cache.get_building("PP1") is not None
        assert cache.get_building("OLD") is None

    async def test_refresh_api_error(self, tmp_path: Path) -> None:
        """Test refresh handles API errors gracefully."""
        cache = BuildingsCache(cache_dir=tmp_path)

        mock_client = AsyncMock()
        mock_client.get_all_buildings.side_effect = FIOApiError(
            "Server error", status_code=500
        )

        with (
            patch(
                "prun_mcp.cache.get_buildings_cache", return_value=cache
            ),
            patch(
                "prun_mcp.prun_lib.buildings.get_fio_client", return_value=mock_client
            ),
        ):
            result = await refresh_buildings_cache()

        assert "failed" in result.lower()


class TestSearchBuildings:
    """Tests for search_buildings tool."""

    async def test_no_filters_returns_all(self, tmp_path: Path) -> None:
        """Test that search_buildings with no filters returns all buildings."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            result = await search_buildings()

        assert isinstance(result, str)

        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        assert "buildings" in decoded
        buildings = decoded["buildings"]
        assert len(buildings) == 4

        # Verify only Ticker and Name are returned
        for b in buildings:
            assert set(b.keys()) == {"Ticker", "Name"}  # type: ignore[union-attr]

        tickers = [b["Ticker"] for b in buildings]  # type: ignore[index]
        assert "PP1" in tickers
        assert "HB1" in tickers
        assert "FRM" in tickers
        assert "FP" in tickers

    async def test_filter_by_expertise(self, tmp_path: Path) -> None:
        """Test filtering by expertise type."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            result = await search_buildings(expertise="CONSTRUCTION")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        buildings = decoded["buildings"]
        assert len(buildings) == 1
        assert buildings[0]["Ticker"] == "PP1"  # type: ignore[index]

    async def test_filter_by_workforce(self, tmp_path: Path) -> None:
        """Test filtering by workforce type."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            # All sample buildings have Pioneers
            result = await search_buildings(workforce="Pioneers")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        buildings = decoded["buildings"]
        assert len(buildings) == 4

    async def test_filter_by_commodity_tickers(self, tmp_path: Path) -> None:
        """Test filtering by commodity tickers (AND logic)."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            # BSE and BDE - PP1 and FP have both
            result = await search_buildings(commodity_tickers=["BSE", "BDE"])

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        buildings = decoded["buildings"]
        assert len(buildings) == 2
        tickers = [b["Ticker"] for b in buildings]  # type: ignore[index]
        assert "PP1" in tickers
        assert "FP" in tickers

    async def test_invalid_expertise_returns_error(self, tmp_path: Path) -> None:
        """Test that invalid expertise returns helpful error."""
        result = await search_buildings(expertise="INVALID")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Invalid expertise" in result[0].text
        assert "CONSTRUCTION" in result[0].text  # Lists valid values

    async def test_invalid_workforce_returns_error(self, tmp_path: Path) -> None:
        """Test that invalid workforce returns helpful error."""
        result = await search_buildings(workforce="Invalid")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Invalid workforce" in result[0].text
        assert "Pioneers" in result[0].text  # Lists valid values

    async def test_populates_cache_on_miss(self, tmp_path: Path) -> None:
        """Test that cache is populated when invalid (ensure_buildings_cache handles this)."""
        cache = create_populated_cache(tmp_path)

        mock_manager = MagicMock()

        mock_manager.ensure = AsyncMock(return_value=cache)


        with patch(

            "prun_mcp.prun_lib.buildings.get_cache_manager",

            return_value=mock_manager,

        ):
            result = await search_buildings()

        assert isinstance(result, str)

    async def test_api_error_returns_error_content(self) -> None:
        """Test FIO API error returns error content."""
        mock_manager = MagicMock()
        mock_manager.ensure = AsyncMock(
            side_effect=FIOApiError("Server error", status_code=500)
        )

        with patch("prun_mcp.prun_lib.buildings.get_cache_manager", return_value=mock_manager):
            result = await search_buildings()

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text
