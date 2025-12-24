"""Tests for the JSON-based recipes cache."""

from pathlib import Path

from prun_mcp.cache import RecipesCache

from tests.conftest import SAMPLE_RECIPES


class TestRecipesCache:
    """Tests for RecipesCache class."""

    def test_cache_starts_empty(self, tmp_path: Path) -> None:
        """Test that a new cache starts with no valid data."""
        cache = RecipesCache(cache_dir=tmp_path)
        assert not cache.is_valid()
        assert cache.recipe_count() == 0

    def test_refresh_populates_cache(self, tmp_path: Path) -> None:
        """Test that refresh() populates the cache with recipes."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        assert cache.is_valid()
        assert cache.recipe_count() == 5

    def test_get_recipes_by_output(self, tmp_path: Path) -> None:
        """Test that get_recipes_by_output returns recipes that produce a material."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        # RAT has 2 recipes that produce it
        rat_recipes = cache.get_recipes_by_output("RAT")
        assert len(rat_recipes) == 2
        for recipe in rat_recipes:
            assert recipe["BuildingTicker"] == "FP"
            outputs = [o["Ticker"] for o in recipe["Outputs"]]
            assert "RAT" in outputs

    def test_get_recipes_by_output_case_insensitive(self, tmp_path: Path) -> None:
        """Test that get_recipes_by_output handles lowercase tickers."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        recipes = cache.get_recipes_by_output("rat")
        assert len(recipes) == 2

    def test_get_recipes_by_output_not_found(self, tmp_path: Path) -> None:
        """Test that get_recipes_by_output returns empty list for unknown ticker."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        recipes = cache.get_recipes_by_output("NOTEXIST")
        assert recipes == []

    def test_get_recipes_by_output_cache_invalid(self, tmp_path: Path) -> None:
        """Test that get_recipes_by_output returns empty list when cache is invalid."""
        cache = RecipesCache(cache_dir=tmp_path)

        recipes = cache.get_recipes_by_output("RAT")
        assert recipes == []

    def test_get_all_recipes(self, tmp_path: Path) -> None:
        """Test that get_all_recipes returns all recipes."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        recipes = cache.get_all_recipes()
        assert len(recipes) == 5

    def test_invalidate_clears_cache(self, tmp_path: Path) -> None:
        """Test that invalidate() clears the cache file."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)
        assert cache.is_valid()

        cache.invalidate()
        assert not cache.is_valid()
        assert cache.recipe_count() == 0
        assert not cache.cache_file.exists()

    def test_cache_persists_to_file(self, tmp_path: Path) -> None:
        """Test that cache data persists to JSON file."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        # Create new cache instance pointing to same directory
        cache2 = RecipesCache(cache_dir=tmp_path)
        assert cache2.is_valid()

        recipes = cache2.get_recipes_by_output("BSE")
        assert len(recipes) == 1
        assert recipes[0]["BuildingTicker"] == "PP1"

    def test_cache_creates_directory(self, tmp_path: Path) -> None:
        """Test that cache creates the cache directory if it doesn't exist."""
        cache_dir = tmp_path / "nested" / "cache"
        cache = RecipesCache(cache_dir=cache_dir)

        cache.refresh(SAMPLE_RECIPES)

        assert cache_dir.exists()
        assert cache.cache_file.exists()

    def test_ttl_expiration(self, tmp_path: Path) -> None:
        """Test that cache becomes invalid after TTL expires."""
        # Use very short TTL for testing (0 hours = immediately expired)
        cache = RecipesCache(cache_dir=tmp_path, ttl_hours=0)
        cache.refresh(SAMPLE_RECIPES)

        # Cache should be invalid immediately with 0 TTL
        assert not cache.is_valid()

    def test_recipe_count_loads_from_file(self, tmp_path: Path) -> None:
        """Test that recipe_count loads from file if not in memory."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        # Create new instance that hasn't loaded data yet
        cache2 = RecipesCache(cache_dir=tmp_path)
        assert cache2._recipes is None  # Not loaded yet

        count = cache2.recipe_count()
        assert count == 5
        assert cache2._recipes is not None  # Now loaded

    def test_search_recipes_no_filters(self, tmp_path: Path) -> None:
        """Test that search_recipes with no filters returns all recipes."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        recipes = cache.search_recipes()
        assert isinstance(recipes, list)
        assert len(recipes) == 5

    def test_search_recipes_empty_cache(self, tmp_path: Path) -> None:
        """Test that search_recipes returns empty list when cache is invalid."""
        cache = RecipesCache(cache_dir=tmp_path)

        recipes = cache.search_recipes()
        assert recipes == []

    def test_search_recipes_by_building(self, tmp_path: Path) -> None:
        """Test filtering by building ticker."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        # Filter by PP1 - should find 2 recipes
        recipes = cache.search_recipes(building="PP1")
        assert len(recipes) == 2
        for r in recipes:
            assert r["BuildingTicker"] == "PP1"

        # Filter by FP - should find 2 recipes
        recipes = cache.search_recipes(building="FP")
        assert len(recipes) == 2
        for r in recipes:
            assert r["BuildingTicker"] == "FP"

    def test_search_recipes_building_case_insensitive(self, tmp_path: Path) -> None:
        """Test that building filter is case-insensitive."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        recipes = cache.search_recipes(building="pp1")
        assert len(recipes) == 2

    def test_search_recipes_by_input_tickers(self, tmp_path: Path) -> None:
        """Test filtering by input tickers (AND logic)."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        # Filter by BEA - 2 recipes use it as input
        recipes = cache.search_recipes(input_tickers=["BEA"])
        assert len(recipes) == 2

        # Filter by GRN and BEA - only 1 recipe uses both
        recipes = cache.search_recipes(input_tickers=["GRN", "BEA"])
        assert len(recipes) == 1
        assert recipes[0]["RecipeName"] == "1xGRN 1xBEA 1xNUT=>10xRAT"

    def test_search_recipes_by_output_tickers(self, tmp_path: Path) -> None:
        """Test filtering by output tickers (AND logic)."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        # Filter by RAT - 2 recipes produce it
        recipes = cache.search_recipes(output_tickers=["RAT"])
        assert len(recipes) == 2

        # Filter by BSE - 1 recipe produces it
        recipes = cache.search_recipes(output_tickers=["BSE"])
        assert len(recipes) == 1
        assert recipes[0]["BuildingTicker"] == "PP1"

    def test_search_recipes_input_tickers_case_insensitive(
        self, tmp_path: Path
    ) -> None:
        """Test that input tickers filter is case-insensitive."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        recipes = cache.search_recipes(input_tickers=["bea"])
        assert len(recipes) == 2

    def test_search_recipes_combined_filters(self, tmp_path: Path) -> None:
        """Test combining multiple filters (AND logic)."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        # Filter by building and output
        recipes = cache.search_recipes(building="FP", output_tickers=["RAT"])
        assert len(recipes) == 2

        # Filter by building, input, and output
        recipes = cache.search_recipes(
            building="FP", input_tickers=["GRN"], output_tickers=["RAT"]
        )
        assert len(recipes) == 1
        assert recipes[0]["RecipeName"] == "1xGRN 1xBEA 1xNUT=>10xRAT"

    def test_search_recipes_loads_from_file(self, tmp_path: Path) -> None:
        """Test that search_recipes loads from file if not in memory."""
        cache = RecipesCache(cache_dir=tmp_path)
        cache.refresh(SAMPLE_RECIPES)

        # Create new instance that hasn't loaded data yet
        cache2 = RecipesCache(cache_dir=tmp_path)
        assert cache2._recipes is None  # Not loaded yet

        recipes = cache2.search_recipes()
        assert len(recipes) == 5
        assert cache2._recipes is not None  # Now loaded
