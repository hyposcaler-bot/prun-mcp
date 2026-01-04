"""JSON-based caching layer for FIO API data."""

from prun_mcp.cache.buildings_cache import BuildingsCache
from prun_mcp.cache.materials_cache import MaterialsCache
from prun_mcp.cache.recipes_cache import RecipesCache
from prun_mcp.cache.workforce_cache import WorkforceCache

__all__ = [
    "BuildingsCache",
    "MaterialsCache",
    "RecipesCache",
    "WorkforceCache",
    # Singleton getters
    "get_buildings_cache",
    "get_materials_cache",
    "get_recipes_cache",
    "get_workforce_cache",
    # Ensure functions
    "ensure_buildings_cache",
    "ensure_materials_cache",
    "ensure_recipes_cache",
    "ensure_workforce_cache",
]

# Singleton instances
_buildings_cache: BuildingsCache | None = None
_materials_cache: MaterialsCache | None = None
_recipes_cache: RecipesCache | None = None
_workforce_cache: WorkforceCache | None = None


def get_buildings_cache() -> BuildingsCache:
    """Get or create the shared buildings cache."""
    global _buildings_cache
    if _buildings_cache is None:
        _buildings_cache = BuildingsCache()
    return _buildings_cache


def get_materials_cache() -> MaterialsCache:
    """Get or create the shared materials cache."""
    global _materials_cache
    if _materials_cache is None:
        _materials_cache = MaterialsCache()
    return _materials_cache


def get_recipes_cache() -> RecipesCache:
    """Get or create the shared recipes cache."""
    global _recipes_cache
    if _recipes_cache is None:
        _recipes_cache = RecipesCache()
    return _recipes_cache


def get_workforce_cache() -> WorkforceCache:
    """Get or create the shared workforce cache."""
    global _workforce_cache
    if _workforce_cache is None:
        _workforce_cache = WorkforceCache()
    return _workforce_cache


async def ensure_buildings_cache() -> BuildingsCache:
    """Ensure the buildings cache is populated and return it."""
    from prun_mcp.fio import get_fio_client

    cache = get_buildings_cache()
    if not cache.is_valid():
        client = get_fio_client()
        buildings = await client.get_all_buildings()
        cache.refresh(buildings)
    return cache


async def ensure_materials_cache() -> MaterialsCache:
    """Ensure the materials cache is populated and return it."""
    from prun_mcp.fio import get_fio_client

    cache = get_materials_cache()
    if not cache.is_valid():
        client = get_fio_client()
        materials = await client.get_all_materials()
        cache.refresh(materials)
    return cache


async def ensure_recipes_cache() -> RecipesCache:
    """Ensure the recipes cache is populated and return it."""
    from prun_mcp.fio import get_fio_client

    cache = get_recipes_cache()
    if not cache.is_valid():
        client = get_fio_client()
        recipes = await client.get_all_recipes()
        cache.refresh(recipes)
    return cache


async def ensure_workforce_cache() -> WorkforceCache:
    """Ensure the workforce cache is populated and return it."""
    from prun_mcp.fio import get_fio_client

    cache = get_workforce_cache()
    if not cache.is_valid():
        client = get_fio_client()
        workforce = await client.get_workforce_needs()
        cache.refresh(workforce)
    return cache
