"""JSON-based caching layer for FIO API data."""

from enum import Enum
from typing import Any, Literal, overload

from prun_mcp.cache.buildings_cache import BuildingsCache
from prun_mcp.cache.materials_cache import MaterialsCache
from prun_mcp.cache.recipes_cache import RecipesCache
from prun_mcp.cache.workforce_cache import WorkforceCache

__all__ = [
    "BuildingsCache",
    "MaterialsCache",
    "RecipesCache",
    "WorkforceCache",
    "CacheManager",
    "CacheType",
    "get_cache_manager",
    # Deprecated - for backward compatibility with tests
    "get_buildings_cache",
    "get_materials_cache",
    "get_recipes_cache",
    "get_workforce_cache",
    "ensure_buildings_cache",
    "ensure_materials_cache",
    "ensure_recipes_cache",
    "ensure_workforce_cache",
]


class CacheType(str, Enum):
    """Cache type identifiers."""

    BUILDINGS = "buildings"
    MATERIALS = "materials"
    RECIPES = "recipes"
    WORKFORCE = "workforce"


class CacheManager:
    """Centralized cache management with lazy initialization."""

    def __init__(self) -> None:
        """Initialize the cache manager."""
        self._caches: dict[
            CacheType,
            BuildingsCache | MaterialsCache | RecipesCache | WorkforceCache | None,
        ] = {
            CacheType.BUILDINGS: None,
            CacheType.MATERIALS: None,
            CacheType.RECIPES: None,
            CacheType.WORKFORCE: None,
        }
        self._cache_classes: dict[CacheType, type] = {
            CacheType.BUILDINGS: BuildingsCache,
            CacheType.MATERIALS: MaterialsCache,
            CacheType.RECIPES: RecipesCache,
            CacheType.WORKFORCE: WorkforceCache,
        }

    @overload
    def get(self, cache_type: Literal[CacheType.BUILDINGS]) -> BuildingsCache: ...

    @overload
    def get(self, cache_type: Literal[CacheType.MATERIALS]) -> MaterialsCache: ...

    @overload
    def get(self, cache_type: Literal[CacheType.RECIPES]) -> RecipesCache: ...

    @overload
    def get(self, cache_type: Literal[CacheType.WORKFORCE]) -> WorkforceCache: ...

    def get(
        self, cache_type: CacheType
    ) -> BuildingsCache | MaterialsCache | RecipesCache | WorkforceCache:
        """Get or create a cache instance.

        Args:
            cache_type: Type of cache to retrieve.

        Returns:
            The cache instance for the specified type.
        """
        if self._caches[cache_type] is None:
            self._caches[cache_type] = self._cache_classes[cache_type]()
        return self._caches[cache_type]  # type: ignore[return-value]

    @overload
    async def ensure(
        self, cache_type: Literal[CacheType.BUILDINGS]
    ) -> BuildingsCache: ...

    @overload
    async def ensure(
        self, cache_type: Literal[CacheType.MATERIALS]
    ) -> MaterialsCache: ...

    @overload
    async def ensure(self, cache_type: Literal[CacheType.RECIPES]) -> RecipesCache: ...

    @overload
    async def ensure(
        self, cache_type: Literal[CacheType.WORKFORCE]
    ) -> WorkforceCache: ...

    async def ensure(
        self, cache_type: CacheType
    ) -> BuildingsCache | MaterialsCache | RecipesCache | WorkforceCache:
        """Ensure cache is populated and return it.

        Args:
            cache_type: Type of cache to ensure.

        Returns:
            The populated cache instance.
        """
        from prun_mcp.fio import get_fio_client

        cache = self.get(cache_type)
        if not cache.is_valid():
            client = get_fio_client()
            data = await self._fetch_data(client, cache_type)
            cache.refresh(data)
        return cache

    async def _fetch_data(
        self, client: Any, cache_type: CacheType
    ) -> list[dict[str, Any]]:
        """Fetch data from FIO API based on cache type.

        Args:
            client: FIO API client.
            cache_type: Type of cache to fetch data for.

        Returns:
            List of data from the API.
        """
        fetch_methods = {
            CacheType.BUILDINGS: client.get_all_buildings,
            CacheType.MATERIALS: client.get_all_materials,
            CacheType.RECIPES: client.get_all_recipes,
            CacheType.WORKFORCE: client.get_workforce_needs,
        }
        return await fetch_methods[cache_type]()

    def reset(self) -> None:
        """Reset all caches (useful for testing)."""
        for cache_type in CacheType:
            self._caches[cache_type] = None


# Singleton instance
_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance.

    Returns:
        The singleton CacheManager instance.
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# Deprecated wrapper functions for backward compatibility with tests
def get_buildings_cache() -> BuildingsCache:
    """Get or create the shared buildings cache.

    .. deprecated::
        Use get_cache_manager().get(CacheType.BUILDINGS) instead.
    """
    return get_cache_manager().get(CacheType.BUILDINGS)


def get_materials_cache() -> MaterialsCache:
    """Get or create the shared materials cache.

    .. deprecated::
        Use get_cache_manager().get(CacheType.MATERIALS) instead.
    """
    return get_cache_manager().get(CacheType.MATERIALS)


def get_recipes_cache() -> RecipesCache:
    """Get or create the shared recipes cache.

    .. deprecated::
        Use get_cache_manager().get(CacheType.RECIPES) instead.
    """
    return get_cache_manager().get(CacheType.RECIPES)


def get_workforce_cache() -> WorkforceCache:
    """Get or create the shared workforce cache.

    .. deprecated::
        Use get_cache_manager().get(CacheType.WORKFORCE) instead.
    """
    return get_cache_manager().get(CacheType.WORKFORCE)


async def ensure_buildings_cache() -> BuildingsCache:
    """Ensure the buildings cache is populated and return it.

    .. deprecated::
        Use await get_cache_manager().ensure(CacheType.BUILDINGS) instead.
    """
    return await get_cache_manager().ensure(CacheType.BUILDINGS)


async def ensure_materials_cache() -> MaterialsCache:
    """Ensure the materials cache is populated and return it.

    .. deprecated::
        Use await get_cache_manager().ensure(CacheType.MATERIALS) instead.
    """
    return await get_cache_manager().ensure(CacheType.MATERIALS)


async def ensure_recipes_cache() -> RecipesCache:
    """Ensure the recipes cache is populated and return it.

    .. deprecated::
        Use await get_cache_manager().ensure(CacheType.RECIPES) instead.
    """
    return await get_cache_manager().ensure(CacheType.RECIPES)


async def ensure_workforce_cache() -> WorkforceCache:
    """Ensure the workforce cache is populated and return it.

    .. deprecated::
        Use await get_cache_manager().ensure(CacheType.WORKFORCE) instead.
    """
    return await get_cache_manager().ensure(CacheType.WORKFORCE)
