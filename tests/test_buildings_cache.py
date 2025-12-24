"""Tests for the JSON-based buildings cache."""

from pathlib import Path

from prun_mcp.cache import BuildingsCache

from tests.conftest import SAMPLE_BUILDINGS


class TestBuildingsCache:
    """Tests for BuildingsCache class."""

    def test_cache_starts_empty(self, tmp_path: Path) -> None:
        """Test that a new cache starts with no valid data."""
        cache = BuildingsCache(cache_dir=tmp_path)
        assert not cache.is_valid()
        assert cache.building_count() == 0

    def test_refresh_populates_cache(self, tmp_path: Path) -> None:
        """Test that refresh() populates the cache with buildings."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        assert cache.is_valid()
        assert cache.building_count() == 3

    def test_get_building_returns_full_data(self, tmp_path: Path) -> None:
        """Test that get_building returns data with costs, recipes, and workforce."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        building = cache.get_building("PP1")
        assert building is not None
        assert building["Ticker"] == "PP1"
        assert building["Name"] == "prefabPlant1"
        assert building["AreaCost"] == 19
        assert building["Expertise"] == "CONSTRUCTION"

        # Check construction costs (nested list)
        assert "BuildingCosts" in building
        costs = building["BuildingCosts"]
        assert len(costs) == 3
        assert any(c["CommodityTicker"] == "BSE" and c["Amount"] == 4 for c in costs)

        # Check workforce fields
        assert building["Pioneers"] == 80
        assert building["Settlers"] == 0

        # Check recipes (nested list)
        assert "Recipes" in building
        assert len(building["Recipes"]) == 1

    def test_get_building_case_insensitive(self, tmp_path: Path) -> None:
        """Test that get_building handles lowercase tickers."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        building = cache.get_building("pp1")
        assert building is not None
        assert building["Ticker"] == "PP1"

    def test_get_building_not_found(self, tmp_path: Path) -> None:
        """Test that get_building returns None for unknown ticker."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        building = cache.get_building("NOTEXIST")
        assert building is None

    def test_get_building_cache_invalid(self, tmp_path: Path) -> None:
        """Test that get_building returns None when cache is invalid."""
        cache = BuildingsCache(cache_dir=tmp_path)

        building = cache.get_building("PP1")
        assert building is None

    def test_invalidate_clears_cache(self, tmp_path: Path) -> None:
        """Test that invalidate() clears the cache file."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)
        assert cache.is_valid()

        cache.invalidate()
        assert not cache.is_valid()
        assert cache.building_count() == 0
        assert not cache.cache_file.exists()

    def test_cache_persists_to_file(self, tmp_path: Path) -> None:
        """Test that cache data persists to JSON file."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        # Create new cache instance pointing to same directory
        cache2 = BuildingsCache(cache_dir=tmp_path)
        assert cache2.is_valid()

        building = cache2.get_building("FRM")
        assert building is not None
        assert building["Name"] == "farmstead"

    def test_cache_creates_directory(self, tmp_path: Path) -> None:
        """Test that cache creates the cache directory if it doesn't exist."""
        cache_dir = tmp_path / "nested" / "cache"
        cache = BuildingsCache(cache_dir=cache_dir)

        cache.refresh(SAMPLE_BUILDINGS)

        assert cache_dir.exists()
        assert cache.cache_file.exists()

    def test_ttl_expiration(self, tmp_path: Path) -> None:
        """Test that cache becomes invalid after TTL expires."""
        # Use very short TTL for testing (0 hours = immediately expired)
        cache = BuildingsCache(cache_dir=tmp_path, ttl_hours=0)
        cache.refresh(SAMPLE_BUILDINGS)

        # Cache should be invalid immediately with 0 TTL
        assert not cache.is_valid()

    def test_building_with_null_expertise(self, tmp_path: Path) -> None:
        """Test handling of building with null expertise field."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        building = cache.get_building("HB1")
        assert building is not None
        assert building["Expertise"] is None

    def test_building_count_loads_from_file(self, tmp_path: Path) -> None:
        """Test that building_count loads from file if not in memory."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        # Create new instance that hasn't loaded data yet
        cache2 = BuildingsCache(cache_dir=tmp_path)
        assert cache2._buildings is None  # Not loaded yet

        count = cache2.building_count()
        assert count == 3
        assert cache2._buildings is not None  # Now loaded

    def test_search_buildings_no_filters(self, tmp_path: Path) -> None:
        """Test that search_buildings with no filters returns all buildings."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        buildings = cache.search_buildings()
        assert isinstance(buildings, list)
        assert len(buildings) == 3

        # Verify only Ticker and Name are returned
        for b in buildings:
            assert set(b.keys()) == {"Ticker", "Name"}

        tickers = [b["Ticker"] for b in buildings]
        assert "PP1" in tickers
        assert "HB1" in tickers
        assert "FRM" in tickers

    def test_search_buildings_empty_cache(self, tmp_path: Path) -> None:
        """Test that search_buildings returns empty list when cache is invalid."""
        cache = BuildingsCache(cache_dir=tmp_path)

        buildings = cache.search_buildings()
        assert buildings == []

    def test_search_buildings_by_expertise(self, tmp_path: Path) -> None:
        """Test filtering by expertise."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        # Filter by CONSTRUCTION - should find PP1
        buildings = cache.search_buildings(expertise="CONSTRUCTION")
        assert len(buildings) == 1
        assert buildings[0]["Ticker"] == "PP1"

        # Filter by AGRICULTURE - should find FRM
        buildings = cache.search_buildings(expertise="AGRICULTURE")
        assert len(buildings) == 1
        assert buildings[0]["Ticker"] == "FRM"

    def test_search_buildings_expertise_case_insensitive(self, tmp_path: Path) -> None:
        """Test that expertise filter is case-insensitive."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        buildings = cache.search_buildings(expertise="construction")
        assert len(buildings) == 1
        assert buildings[0]["Ticker"] == "PP1"

    def test_search_buildings_by_workforce(self, tmp_path: Path) -> None:
        """Test filtering by workforce type."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        # All buildings have Pioneers > 0
        buildings = cache.search_buildings(workforce="Pioneers")
        assert len(buildings) == 3

        # No buildings have Settlers > 0
        buildings = cache.search_buildings(workforce="Settlers")
        assert len(buildings) == 0

    def test_search_buildings_by_commodity_tickers(self, tmp_path: Path) -> None:
        """Test filtering by commodity tickers (AND logic)."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        # Filter by BSE - all 3 buildings use it
        buildings = cache.search_buildings(commodity_tickers=["BSE"])
        assert len(buildings) == 3

        # Filter by BSE and BBH - all 3 buildings use both
        buildings = cache.search_buildings(commodity_tickers=["BSE", "BBH"])
        assert len(buildings) == 3

        # Filter by BSE and BDE - only PP1 has both
        buildings = cache.search_buildings(commodity_tickers=["BSE", "BDE"])
        assert len(buildings) == 1
        assert buildings[0]["Ticker"] == "PP1"

    def test_search_buildings_commodity_tickers_case_insensitive(
        self, tmp_path: Path
    ) -> None:
        """Test that commodity tickers filter is case-insensitive."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        buildings = cache.search_buildings(commodity_tickers=["bse"])
        assert len(buildings) == 3

    def test_search_buildings_combined_filters(self, tmp_path: Path) -> None:
        """Test combining multiple filters (AND logic)."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        # Filter by expertise and commodity ticker
        buildings = cache.search_buildings(
            expertise="CONSTRUCTION", commodity_tickers=["BSE"]
        )
        assert len(buildings) == 1
        assert buildings[0]["Ticker"] == "PP1"

        # Filter by expertise and workforce
        buildings = cache.search_buildings(
            expertise="AGRICULTURE", workforce="Pioneers"
        )
        assert len(buildings) == 1
        assert buildings[0]["Ticker"] == "FRM"

    def test_search_buildings_loads_from_file(self, tmp_path: Path) -> None:
        """Test that search_buildings loads from file if not in memory."""
        cache = BuildingsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_BUILDINGS)

        # Create new instance that hasn't loaded data yet
        cache2 = BuildingsCache(cache_dir=tmp_path)
        assert cache2._buildings is None  # Not loaded yet

        buildings = cache2.search_buildings()
        assert len(buildings) == 3
        assert cache2._buildings is not None  # Now loaded
