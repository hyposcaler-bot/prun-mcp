"""JSON-based cache storage for recipe data."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RecipesCache:
    """Cache for recipe data stored as JSON.

    Recipes are indexed by output ticker for efficient lookup of recipes
    that produce a specific material.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_hours: int = 24,
    ) -> None:
        """Initialize the recipes cache.

        Args:
            cache_dir: Directory for cache files. Defaults to 'cache' in current directory.
            ttl_hours: Time-to-live for cache in hours. Defaults to 24.
        """
        self.cache_dir = cache_dir or Path("cache")
        self.cache_file = self.cache_dir / "recipes.json"
        self.ttl_hours = ttl_hours
        self._recipes: list[dict[str, Any]] | None = None
        self._recipes_by_output: dict[str, list[dict[str, Any]]] | None = None
        self._loaded_at: datetime | None = None

    def is_valid(self) -> bool:
        """Check if the cache file exists and is within TTL.

        Returns:
            True if cache is valid, False otherwise.
        """
        if not self.cache_file.exists():
            return False

        mtime = datetime.fromtimestamp(self.cache_file.stat().st_mtime)
        age = datetime.now() - mtime
        return age < timedelta(hours=self.ttl_hours)

    def _load(self) -> None:
        """Load recipes from JSON file into memory."""
        if not self.cache_file.exists():
            self._recipes = None
            self._recipes_by_output = None
            self._loaded_at = None
            return

        with open(self.cache_file, encoding="utf-8") as f:
            recipes: list[dict[str, Any]] = json.load(f)

        self._recipes = recipes

        # Build index by output ticker
        self._recipes_by_output = {}
        for recipe in recipes:
            for output in recipe.get("Outputs", []):
                ticker = output.get("Ticker", "").upper()
                if ticker:
                    if ticker not in self._recipes_by_output:
                        self._recipes_by_output[ticker] = []
                    self._recipes_by_output[ticker].append(recipe)

        self._loaded_at = datetime.now()
        logger.info("Loaded %d recipes from cache", len(recipes))

    def get_recipes_by_output(self, ticker: str) -> list[dict[str, Any]]:
        """Get all recipes that produce a specific material.

        Args:
            ticker: Material ticker symbol (e.g., "BSE", "RAT").

        Returns:
            List of recipes that produce this material, or empty list if not found.
        """
        if self._recipes is None or not self.is_valid():
            if self.is_valid():
                self._load()
            else:
                return []

        if not self._recipes_by_output:
            return []

        return self._recipes_by_output.get(ticker.upper(), [])

    def get_all_recipes(self) -> list[dict[str, Any]]:
        """Get all recipes from the cache.

        Returns:
            List of all recipes, or empty list if cache is invalid.
        """
        if self._recipes is None and self.is_valid():
            self._load()

        return self._recipes if self._recipes else []

    def refresh(self, recipes: list[dict[str, Any]]) -> None:
        """Refresh the cache with new recipe data.

        Args:
            recipes: List of recipe dictionaries from FIO API.
        """
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Write JSON content to file
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(recipes, f)

        # Load into memory
        self._recipes = recipes

        # Build index by output ticker
        self._recipes_by_output = {}
        for recipe in self._recipes:
            for output in recipe.get("Outputs", []):
                ticker = output.get("Ticker", "").upper()
                if ticker:
                    if ticker not in self._recipes_by_output:
                        self._recipes_by_output[ticker] = []
                    self._recipes_by_output[ticker].append(recipe)

        self._loaded_at = datetime.now()
        logger.info("Refreshed cache with %d recipes", len(self._recipes))

    def invalidate(self) -> None:
        """Invalidate the cache by deleting the cache file."""
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("Recipes cache invalidated")

        self._recipes = None
        self._recipes_by_output = None
        self._loaded_at = None

    def recipe_count(self) -> int:
        """Get the number of recipes in the cache.

        Returns:
            Number of cached recipes, or 0 if cache is not loaded.
        """
        if self._recipes is None and self.is_valid():
            self._load()
        return len(self._recipes) if self._recipes else 0

    def search_recipes(
        self,
        building: str | None = None,
        input_tickers: list[str] | None = None,
        output_tickers: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search recipes with optional filters.

        Args:
            building: Building ticker to filter by (case-insensitive).
            input_tickers: Input material tickers to filter by.
                Recipes must use ALL specified materials as inputs (AND logic).
            output_tickers: Output material tickers to filter by.
                Recipes must produce ALL specified materials as outputs (AND logic).

        Returns:
            List of matching recipes with BuildingTicker, RecipeName,
            Inputs, Outputs, and TimeMs. Returns empty list if cache is invalid.
        """
        if self._recipes is None and self.is_valid():
            self._load()

        if not self._recipes:
            return []

        results = list(self._recipes)

        # Filter by building ticker (case-insensitive)
        if building:
            upper_building = building.upper()
            results = [
                r
                for r in results
                if r.get("BuildingTicker", "").upper() == upper_building
            ]

        # Filter by input tickers (AND logic - must have ALL)
        if input_tickers:
            upper_inputs = {t.upper() for t in input_tickers}
            filtered = []
            for recipe in results:
                recipe_inputs = {
                    inp.get("Ticker", "").upper() for inp in recipe.get("Inputs", [])
                }
                if upper_inputs.issubset(recipe_inputs):
                    filtered.append(recipe)
            results = filtered

        # Filter by output tickers (AND logic - must have ALL)
        if output_tickers:
            upper_outputs = {t.upper() for t in output_tickers}
            filtered = []
            for recipe in results:
                recipe_outputs = {
                    out.get("Ticker", "").upper() for out in recipe.get("Outputs", [])
                }
                if upper_outputs.issubset(recipe_outputs):
                    filtered.append(recipe)
            results = filtered

        return results
