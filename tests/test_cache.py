"""Tests for the JSON-based materials cache."""

from pathlib import Path

from prun_mcp.cache import MaterialsCache

from tests.conftest import SAMPLE_MATERIALS


class TestMaterialsCache:
    """Tests for MaterialsCache class."""

    def test_cache_starts_empty(self, tmp_path: Path) -> None:
        """Test that a new cache starts with no valid data."""
        cache = MaterialsCache(cache_dir=tmp_path)
        assert not cache.is_valid()
        assert cache.material_count() == 0

    def test_refresh_populates_cache(self, tmp_path: Path) -> None:
        """Test that refresh() populates the cache with materials."""
        cache = MaterialsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_MATERIALS)

        assert cache.is_valid()
        assert cache.material_count() == 3

    def test_get_material_returns_data(self, tmp_path: Path) -> None:
        """Test that get_material returns correct data for known ticker."""
        cache = MaterialsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_MATERIALS)

        material = cache.get_material("BSE")
        assert material is not None
        assert material["Ticker"] == "BSE"
        assert material["Name"] == "basicStructuralElements"
        assert material["CategoryName"] == "construction prefabs"

    def test_get_material_case_insensitive(self, tmp_path: Path) -> None:
        """Test that get_material handles lowercase tickers."""
        cache = MaterialsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_MATERIALS)

        material = cache.get_material("bse")
        assert material is not None
        assert material["Ticker"] == "BSE"

    def test_get_material_not_found(self, tmp_path: Path) -> None:
        """Test that get_material returns None for unknown ticker."""
        cache = MaterialsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_MATERIALS)

        material = cache.get_material("NOTEXIST")
        assert material is None

    def test_get_material_cache_invalid(self, tmp_path: Path) -> None:
        """Test that get_material returns None when cache is invalid."""
        cache = MaterialsCache(cache_dir=tmp_path)

        material = cache.get_material("BSE")
        assert material is None

    def test_invalidate_clears_cache(self, tmp_path: Path) -> None:
        """Test that invalidate() clears the cache."""
        cache = MaterialsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_MATERIALS)
        assert cache.is_valid()

        cache.invalidate()
        assert not cache.is_valid()
        assert cache.material_count() == 0

    def test_cache_persists_to_file(self, tmp_path: Path) -> None:
        """Test that cache data persists to JSON file."""
        cache = MaterialsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_MATERIALS)

        # Create new cache instance pointing to same directory
        cache2 = MaterialsCache(cache_dir=tmp_path)
        assert cache2.is_valid()

        material = cache2.get_material("RAT")
        assert material is not None
        assert material["Name"] == "rations"

    def test_cache_creates_directory(self, tmp_path: Path) -> None:
        """Test that cache creates the cache directory if it doesn't exist."""
        cache_dir = tmp_path / "nested" / "cache"
        cache = MaterialsCache(cache_dir=cache_dir)

        cache.refresh(SAMPLE_MATERIALS)

        assert cache_dir.exists()
        assert (cache_dir / "materials.json").exists()

    def test_ttl_expiration(self, tmp_path: Path) -> None:
        """Test that cache becomes invalid after TTL expires."""
        # Use very short TTL for testing (0 hours = immediately expired)
        cache = MaterialsCache(cache_dir=tmp_path, ttl_hours=0)
        cache.refresh(SAMPLE_MATERIALS)

        # Cache should be invalid immediately with 0 TTL
        assert not cache.is_valid()

    def test_material_count_loads_from_file(self, tmp_path: Path) -> None:
        """Test that material_count loads from file if not in memory."""
        cache = MaterialsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_MATERIALS)

        # Create new instance that hasn't loaded data yet
        cache2 = MaterialsCache(cache_dir=tmp_path)
        assert cache2._materials is None  # Not loaded yet

        count = cache2.material_count()
        assert count == 3
        assert cache2._materials is not None  # Now loaded

    def test_get_all_materials_returns_list(self, tmp_path: Path) -> None:
        """Test that get_all_materials returns list of all materials."""
        cache = MaterialsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_MATERIALS)

        materials = cache.get_all_materials()
        assert isinstance(materials, list)
        assert len(materials) == 3

        # Check that materials are in the list
        tickers = [m["Ticker"] for m in materials]
        assert "BSE" in tickers
        assert "RAT" in tickers
        assert "H2O" in tickers

    def test_get_all_materials_empty_cache(self, tmp_path: Path) -> None:
        """Test that get_all_materials returns empty list when cache is invalid."""
        cache = MaterialsCache(cache_dir=tmp_path)

        materials = cache.get_all_materials()
        assert materials == []

    def test_get_all_materials_loads_from_file(self, tmp_path: Path) -> None:
        """Test that get_all_materials loads from file if not in memory."""
        cache = MaterialsCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_MATERIALS)

        # Create new instance that hasn't loaded data yet
        cache2 = MaterialsCache(cache_dir=tmp_path)
        assert cache2._materials is None  # Not loaded yet

        materials = cache2.get_all_materials()
        assert len(materials) == 3
        assert cache2._materials is not None  # Now loaded
