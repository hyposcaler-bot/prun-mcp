"""CSV-based cache storage for materials data."""

import csv
import logging
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MaterialsCache:
    """Cache for materials data stored as CSV."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_hours: int = 24,
    ) -> None:
        """Initialize the materials cache.

        Args:
            cache_dir: Directory for cache files. Defaults to 'cache' in current directory.
            ttl_hours: Time-to-live for cache in hours. Defaults to 24.
        """
        self.cache_dir = cache_dir or Path("cache")
        self.cache_file = self.cache_dir / "materials.csv"
        self.ttl_hours = ttl_hours
        self._materials: dict[str, dict[str, Any]] | None = None
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
        """Load materials from CSV file into memory."""
        if not self.cache_file.exists():
            self._materials = None
            self._loaded_at = None
            return

        self._materials = {}
        with open(self.cache_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get("Ticker", row.get("ticker", ""))
                if ticker:
                    self._materials[ticker.upper()] = row

        self._loaded_at = datetime.now()
        logger.info("Loaded %d materials from cache", len(self._materials))

    def get_material(self, ticker: str) -> dict[str, Any] | None:
        """Get a material by ticker from the cache.

        Args:
            ticker: Material ticker symbol (e.g., "BSE", "RAT")

        Returns:
            Material data dictionary or None if not found.
        """
        # Reload if not loaded or cache file was updated
        if self._materials is None or not self.is_valid():
            if self.is_valid():
                self._load()
            else:
                return None

        return self._materials.get(ticker.upper()) if self._materials else None

    def refresh(self, csv_content: str) -> None:
        """Refresh the cache with new CSV content.

        Args:
            csv_content: Raw CSV content from FIO API.
        """
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Write CSV content to file
        with open(self.cache_file, "w", encoding="utf-8") as f:
            f.write(csv_content)

        # Parse and load into memory
        self._materials = {}
        reader = csv.DictReader(StringIO(csv_content))
        for row in reader:
            ticker = row.get("Ticker", row.get("ticker", ""))
            if ticker:
                self._materials[ticker.upper()] = row

        self._loaded_at = datetime.now()
        logger.info("Refreshed cache with %d materials", len(self._materials))

    def invalidate(self) -> None:
        """Invalidate the cache by deleting the cache file."""
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("Cache invalidated")

        self._materials = None
        self._loaded_at = None

    def material_count(self) -> int:
        """Get the number of materials in the cache.

        Returns:
            Number of cached materials, or 0 if cache is not loaded.
        """
        if self._materials is None and self.is_valid():
            self._load()
        return len(self._materials) if self._materials else 0
