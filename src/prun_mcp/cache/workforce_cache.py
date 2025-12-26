"""JSON-based cache storage for workforce needs data."""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(os.environ.get("PRUN_MCP_CACHE_DIR", "cache"))


class WorkforceCache:
    """Cache for workforce consumption needs stored as JSON."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_hours: int = 24,
    ) -> None:
        """Initialize the workforce cache.

        Args:
            cache_dir: Directory for cache files. Defaults to PRUN_MCP_CACHE_DIR
                      env var or 'cache' in current directory.
            ttl_hours: Time-to-live for cache in hours. Defaults to 24.
        """
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_file = self.cache_dir / "workforce.json"
        self.ttl_hours = ttl_hours
        self._workforce: dict[str, list[dict[str, Any]]] | None = None

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
        """Load workforce needs from JSON file into memory."""
        if not self.cache_file.exists():
            self._workforce = None
            return

        self._workforce = {}
        with open(self.cache_file, encoding="utf-8") as f:
            workforce_list = json.load(f)
            for entry in workforce_list:
                workforce_type = entry.get("WorkforceType", "")
                needs = entry.get("Needs", [])
                if workforce_type:
                    self._workforce[workforce_type.upper()] = needs

        logger.info("Loaded %d workforce types from cache", len(self._workforce))

    def get_needs(self, workforce_type: str) -> list[dict[str, Any]] | None:
        """Get consumption needs for a workforce type.

        Args:
            workforce_type: Workforce type (e.g., "PIONEER", "SETTLER")

        Returns:
            List of material needs dictionaries or None if not found.
            Each dict has MaterialTicker and Amount (per 100 workers/day).
        """
        # Reload if not loaded or cache file was updated
        if self._workforce is None or not self.is_valid():
            if self.is_valid():
                self._load()
            else:
                return None

        if not self._workforce:
            return None

        return self._workforce.get(workforce_type.upper())

    def get_all_needs(self) -> dict[str, list[dict[str, Any]]]:
        """Get consumption needs for all workforce types.

        Returns:
            Dict mapping workforce type to list of material needs,
            or empty dict if cache is invalid.
        """
        if not self.is_valid():
            return {}
        if self._workforce is None:
            self._load()
        return self._workforce.copy() if self._workforce else {}

    def refresh(self, workforce_data: list[dict[str, Any]]) -> None:
        """Refresh the cache with new workforce data.

        Args:
            workforce_data: List of workforce needs dictionaries from FIO API.
        """
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Write JSON content to file
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(workforce_data, f)

        # Parse and load into memory
        self._workforce = {}
        for entry in workforce_data:
            workforce_type = entry.get("WorkforceType", "")
            needs = entry.get("Needs", [])
            if workforce_type:
                self._workforce[workforce_type.upper()] = needs

        logger.info("Refreshed cache with %d workforce types", len(self._workforce))

    def invalidate(self) -> None:
        """Invalidate the cache by deleting the cache file."""
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("Workforce cache invalidated")

        self._workforce = None
