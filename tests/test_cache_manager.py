"""Tests for CacheManager class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from prun_mcp.cache import CacheManager, CacheType, get_cache_manager
from prun_mcp.cache.buildings_cache import BuildingsCache
from prun_mcp.cache.materials_cache import MaterialsCache
from prun_mcp.cache.recipes_cache import RecipesCache
from prun_mcp.cache.workforce_cache import WorkforceCache


class TestCacheManager:
    """Tests for CacheManager class."""

    def test_initialization(self) -> None:
        """Test CacheManager initializes with all cache types set to None."""
        manager = CacheManager()

        assert manager._caches[CacheType.BUILDINGS] is None
        assert manager._caches[CacheType.MATERIALS] is None
        assert manager._caches[CacheType.RECIPES] is None
        assert manager._caches[CacheType.WORKFORCE] is None

    def test_get_creates_cache_lazily(self) -> None:
        """Test that get() creates cache instances lazily."""
        manager = CacheManager()

        # Initially no caches created
        assert manager._caches[CacheType.BUILDINGS] is None

        # Get creates the cache
        cache = manager.get(CacheType.BUILDINGS)
        assert cache is not None
        assert isinstance(cache, BuildingsCache)
        assert manager._caches[CacheType.BUILDINGS] is cache

    def test_get_returns_same_instance(self) -> None:
        """Test that get() returns the same instance on subsequent calls."""
        manager = CacheManager()

        cache1 = manager.get(CacheType.BUILDINGS)
        cache2 = manager.get(CacheType.BUILDINGS)

        assert cache1 is cache2

    def test_get_all_cache_types(self) -> None:
        """Test that get() works for all cache types."""
        manager = CacheManager()

        buildings = manager.get(CacheType.BUILDINGS)
        materials = manager.get(CacheType.MATERIALS)
        recipes = manager.get(CacheType.RECIPES)
        workforce = manager.get(CacheType.WORKFORCE)

        assert isinstance(buildings, BuildingsCache)
        assert isinstance(materials, MaterialsCache)
        assert isinstance(recipes, RecipesCache)
        assert isinstance(workforce, WorkforceCache)

    def test_reset_clears_all_caches(self) -> None:
        """Test that reset() clears all cache instances."""
        manager = CacheManager()

        # Create some caches
        manager.get(CacheType.BUILDINGS)
        manager.get(CacheType.MATERIALS)

        # Reset clears them
        manager.reset()

        assert manager._caches[CacheType.BUILDINGS] is None
        assert manager._caches[CacheType.MATERIALS] is None
        assert manager._caches[CacheType.RECIPES] is None
        assert manager._caches[CacheType.WORKFORCE] is None

    @pytest.mark.anyio
    async def test_ensure_returns_cache_if_valid(self) -> None:
        """Test that ensure() returns cache without refreshing if valid."""
        manager = CacheManager()

        # Mock a valid cache
        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = True
        manager._caches[CacheType.BUILDINGS] = mock_cache

        result = await manager.ensure(CacheType.BUILDINGS)

        assert result is mock_cache
        mock_cache.is_valid.assert_called_once()
        mock_cache.refresh.assert_not_called()

    @pytest.mark.anyio
    async def test_ensure_refreshes_invalid_cache(self) -> None:
        """Test that ensure() refreshes cache if invalid."""
        manager = CacheManager()

        # Mock FIO client
        mock_client = AsyncMock()
        mock_client.get_all_buildings.return_value = [{"Ticker": "PP1"}]

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            # Create mock cache that reports as invalid
            mock_cache = MagicMock()
            mock_cache.is_valid.return_value = False
            manager._caches[CacheType.BUILDINGS] = mock_cache

            await manager.ensure(CacheType.BUILDINGS)

            # Verify refresh was called with data from FIO client
            mock_client.get_all_buildings.assert_called_once()
            mock_cache.refresh.assert_called_once_with([{"Ticker": "PP1"}])

    @pytest.mark.anyio
    async def test_ensure_creates_new_cache(self) -> None:
        """Test that ensure() creates cache if it doesn't exist and refreshes if invalid."""
        manager = CacheManager()

        # Mock FIO client
        mock_client = AsyncMock()
        mock_client.get_all_materials.return_value = [{"Ticker": "H2O"}]

        # Mock the cache class to return an invalid cache
        with (
            patch("prun_mcp.fio.get_fio_client", return_value=mock_client),
            patch.object(
                MaterialsCache, "is_valid", return_value=False
            ) as mock_is_valid,
        ):
            cache = await manager.ensure(CacheType.MATERIALS)

            # Cache was created
            assert isinstance(cache, MaterialsCache)
            assert manager._caches[CacheType.MATERIALS] is cache

            # is_valid was called and FIO client was called because it was invalid
            mock_is_valid.assert_called()
            mock_client.get_all_materials.assert_called_once()

    @pytest.mark.anyio
    async def test_fetch_data_buildings(self) -> None:
        """Test _fetch_data for buildings cache type."""
        manager = CacheManager()
        mock_client = AsyncMock()
        mock_client.get_all_buildings.return_value = [{"Ticker": "PP1"}]

        result = await manager._fetch_data(mock_client, CacheType.BUILDINGS)

        assert result == [{"Ticker": "PP1"}]
        mock_client.get_all_buildings.assert_called_once()

    @pytest.mark.anyio
    async def test_fetch_data_materials(self) -> None:
        """Test _fetch_data for materials cache type."""
        manager = CacheManager()
        mock_client = AsyncMock()
        mock_client.get_all_materials.return_value = [{"Ticker": "H2O"}]

        result = await manager._fetch_data(mock_client, CacheType.MATERIALS)

        assert result == [{"Ticker": "H2O"}]
        mock_client.get_all_materials.assert_called_once()

    @pytest.mark.anyio
    async def test_fetch_data_recipes(self) -> None:
        """Test _fetch_data for recipes cache type."""
        manager = CacheManager()
        mock_client = AsyncMock()
        mock_client.get_all_recipes.return_value = [{"RecipeName": "1xH2O=>1xDW"}]

        result = await manager._fetch_data(mock_client, CacheType.RECIPES)

        assert result == [{"RecipeName": "1xH2O=>1xDW"}]
        mock_client.get_all_recipes.assert_called_once()

    @pytest.mark.anyio
    async def test_fetch_data_workforce(self) -> None:
        """Test _fetch_data for workforce cache type."""
        manager = CacheManager()
        mock_client = AsyncMock()
        mock_client.get_workforce_needs.return_value = [{"WorkforceType": "PIONEER"}]

        result = await manager._fetch_data(mock_client, CacheType.WORKFORCE)

        assert result == [{"WorkforceType": "PIONEER"}]
        mock_client.get_workforce_needs.assert_called_once()


class TestGetCacheManager:
    """Tests for get_cache_manager singleton accessor."""

    def test_get_cache_manager_returns_singleton(self) -> None:
        """Test that get_cache_manager returns the same instance."""
        # Reset the global singleton
        import prun_mcp.cache

        prun_mcp.cache._cache_manager = None

        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        assert manager1 is manager2
        assert isinstance(manager1, CacheManager)

    def test_get_cache_manager_creates_instance(self) -> None:
        """Test that get_cache_manager creates instance on first call."""
        # Reset the global singleton
        import prun_mcp.cache

        prun_mcp.cache._cache_manager = None

        manager = get_cache_manager()

        assert isinstance(manager, CacheManager)
        assert prun_mcp.cache._cache_manager is manager
