"""JSON-based cache storage for building data."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BuildingsCache:
    """Cache for building data stored as JSON.

    Buildings are stored with full details including BuildingCosts,
    Recipes, and workforce requirements.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_hours: int = 24,
    ) -> None:
        """Initialize the buildings cache.

        Args:
            cache_dir: Directory for cache files. Defaults to 'cache' in current directory.
            ttl_hours: Time-to-live for cache in hours. Defaults to 24.
        """
        self.cache_dir = cache_dir or Path("cache")
        self.cache_file = self.cache_dir / "buildings.json"
        self.ttl_hours = ttl_hours
        self._buildings: dict[str, dict[str, Any]] | None = None
        self._buildings_by_id: dict[str, dict[str, Any]] | None = None
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
        """Load buildings from JSON file into memory."""
        if not self.cache_file.exists():
            self._buildings = None
            self._buildings_by_id = None
            self._loaded_at = None
            return

        self._buildings = {}
        self._buildings_by_id = {}
        with open(self.cache_file, encoding="utf-8") as f:
            buildings_list = json.load(f)
            for building in buildings_list:
                ticker = building.get("Ticker", "")
                building_id = building.get("BuildingId", "")
                if ticker:
                    self._buildings[ticker.upper()] = building
                if building_id:
                    self._buildings_by_id[building_id.lower()] = building

        self._loaded_at = datetime.now()
        logger.info("Loaded %d buildings from cache", len(self._buildings))

    def get_building(self, identifier: str) -> dict[str, Any] | None:
        """Get a building by ticker or BuildingId from the cache.

        Args:
            identifier: Building ticker symbol (e.g., "PP1", "HB1") or
                       BuildingId (32-character hex string).

        Returns:
            Building data dictionary with full details, or None if not found.
        """
        # Reload if not loaded or cache file was updated
        if self._buildings is None or not self.is_valid():
            if self.is_valid():
                self._load()
            else:
                return None

        if not self._buildings:
            return None

        # Try ticker first (uppercase)
        result = self._buildings.get(identifier.upper())
        if result:
            return result

        # Try BuildingId (lowercase)
        if self._buildings_by_id:
            return self._buildings_by_id.get(identifier.lower())

        return None

    def refresh(self, buildings: list[dict[str, Any]]) -> None:
        """Refresh the cache with new buildings data.

        Args:
            buildings: List of building dictionaries from FIO API.
        """
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Write JSON content to file
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(buildings, f)

        # Parse and load into memory
        self._buildings = {}
        self._buildings_by_id = {}
        for building in buildings:
            ticker = building.get("Ticker", "")
            building_id = building.get("BuildingId", "")
            if ticker:
                self._buildings[ticker.upper()] = building
            if building_id:
                self._buildings_by_id[building_id.lower()] = building

        self._loaded_at = datetime.now()
        logger.info("Refreshed cache with %d buildings", len(self._buildings))

    def invalidate(self) -> None:
        """Invalidate the cache by deleting the cache file."""
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("Buildings cache invalidated")

        self._buildings = None
        self._buildings_by_id = None
        self._loaded_at = None

    def building_count(self) -> int:
        """Get the number of buildings in the cache.

        Returns:
            Number of cached buildings, or 0 if cache is not loaded.
        """
        if self._buildings is None and self.is_valid():
            self._load()
        return len(self._buildings) if self._buildings else 0

    def search_buildings(
        self,
        commodity_tickers: list[str] | None = None,
        expertise: str | None = None,
        workforce: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search buildings with optional filters.

        Args:
            commodity_tickers: Material tickers to filter by. Buildings must use
                ALL specified materials in their construction costs (AND logic).
            expertise: Expertise type to filter by (case-insensitive).
            workforce: Workforce type to filter by. Returns buildings where
                that workforce field is > 0.

        Returns:
            List of matching buildings with Ticker and Name only.
            Use get_building() for full details. Returns empty list if cache is invalid.
        """
        if self._buildings is None and self.is_valid():
            self._load()

        if not self._buildings:
            return []

        results = list(self._buildings.values())

        # Filter by commodity tickers (AND logic - must have ALL)
        if commodity_tickers:
            upper_tickers = {t.upper() for t in commodity_tickers}
            filtered = []
            for building in results:
                building_costs = building.get("BuildingCosts", [])
                building_tickers = {
                    cost.get("CommodityTicker", "").upper() for cost in building_costs
                }
                if upper_tickers.issubset(building_tickers):
                    filtered.append(building)
            results = filtered

        # Filter by expertise (case-insensitive)
        if expertise:
            upper_expertise = expertise.upper()
            results = [
                b
                for b in results
                if b.get("Expertise") is not None
                and b["Expertise"].upper() == upper_expertise
            ]

        # Filter by workforce (field > 0)
        if workforce:
            results = [b for b in results if b.get(workforce, 0) > 0]

        # Return only Ticker and Name for compact results
        return [{"Ticker": b["Ticker"], "Name": b["Name"]} for b in results]
