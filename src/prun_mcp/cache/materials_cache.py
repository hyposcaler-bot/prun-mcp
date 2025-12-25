"""JSON-based cache storage for materials data."""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(os.environ.get("PRUN_MCP_CACHE_DIR", "cache"))


class MaterialsCache:
    """Cache for materials data stored as JSON."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_hours: int = 24,
    ) -> None:
        """Initialize the materials cache.

        Args:
            cache_dir: Directory for cache files. Defaults to PRUN_MCP_CACHE_DIR
                      env var or 'cache' in current directory.
            ttl_hours: Time-to-live for cache in hours. Defaults to 24.
        """
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_file = self.cache_dir / "materials.json"
        self.ttl_hours = ttl_hours
        self._materials: dict[str, dict[str, Any]] | None = None
        self._materials_by_id: dict[str, dict[str, Any]] | None = None

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
        """Load materials from JSON file into memory."""
        if not self.cache_file.exists():
            self._materials = None
            self._materials_by_id = None
            return

        self._materials = {}
        self._materials_by_id = {}
        with open(self.cache_file, encoding="utf-8") as f:
            materials_list = json.load(f)
            for material in materials_list:
                ticker = material.get("Ticker", "")
                material_id = material.get("MaterialId", "")
                if ticker:
                    self._materials[ticker.upper()] = material
                if material_id:
                    self._materials_by_id[material_id.lower()] = material

        logger.info("Loaded %d materials from cache", len(self._materials))

    def get_material(self, identifier: str) -> dict[str, Any] | None:
        """Get a material by ticker or MaterialId from the cache.

        Args:
            identifier: Material ticker symbol (e.g., "BSE", "RAT") or
                       MaterialId (32-character hex string).

        Returns:
            Material data dictionary or None if not found.
        """
        # Reload if not loaded or cache file was updated
        if self._materials is None or not self.is_valid():
            if self.is_valid():
                self._load()
            else:
                return None

        if not self._materials:
            return None

        # Try ticker first (uppercase)
        result = self._materials.get(identifier.upper())
        if result:
            return result

        # Try MaterialId (lowercase)
        if self._materials_by_id:
            return self._materials_by_id.get(identifier.lower())

        return None

    def refresh(self, materials: list[dict[str, Any]]) -> None:
        """Refresh the cache with new materials data.

        Args:
            materials: List of material dictionaries from FIO API.
        """
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Write JSON content to file
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(materials, f)

        # Parse and load into memory
        self._materials = {}
        self._materials_by_id = {}
        for material in materials:
            ticker = material.get("Ticker", "")
            material_id = material.get("MaterialId", "")
            if ticker:
                self._materials[ticker.upper()] = material
            if material_id:
                self._materials_by_id[material_id.lower()] = material

        logger.info("Refreshed cache with %d materials", len(self._materials))

    def invalidate(self) -> None:
        """Invalidate the cache by deleting the cache file."""
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("Cache invalidated")

        self._materials = None
        self._materials_by_id = None

    def material_count(self) -> int:
        """Get the number of materials in the cache.

        Returns:
            Number of cached materials, or 0 if cache is invalid or not loaded.
        """
        if not self.is_valid():
            return 0
        if self._materials is None:
            self._load()
        return len(self._materials) if self._materials else 0

    def get_all_materials(self) -> list[dict[str, Any]]:
        """Get all materials from the cache.

        Returns:
            List of all material dictionaries, or empty list if cache is invalid.
        """
        if not self.is_valid():
            return []
        if self._materials is None:
            self._load()
        return list(self._materials.values()) if self._materials else []
