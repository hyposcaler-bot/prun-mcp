"""Tests for material tools."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent
from toon_format import decode as toon_decode

from prun_mcp.cache import MaterialsCache
from prun_mcp.fio import FIOApiError
from prun_mcp.tools.materials import (
    get_material_info,
    refresh_materials_cache,
)


pytestmark = pytest.mark.anyio


# Sample CSV content matching FIO API format
SAMPLE_CSV = """Ticker,Name,CategoryName,Weight,Volume
BSE,basicStructuralElements,construction prefabs,0.3,0.5
RAT,rations,consumables (basic),0.21,0.1
"""


def create_populated_cache(tmp_path: Path) -> MaterialsCache:
    """Create a cache populated with sample data."""
    cache = MaterialsCache(cache_dir=tmp_path)
    cache.refresh(SAMPLE_CSV)
    return cache


class TestGetMaterialInfo:
    """Tests for get_material_info tool."""

    async def test_returns_toon_encoded_data(self, tmp_path: Path) -> None:
        """Test successful material lookup returns TOON-encoded data."""
        cache = create_populated_cache(tmp_path)

        with patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache):
            result = await get_material_info("BSE")

        assert isinstance(result, str)

        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        assert decoded["Ticker"] == "BSE"  # type: ignore[index]
        assert decoded["Name"] == "basicStructuralElements"  # type: ignore[index]

    async def test_lowercase_ticker_converted(self, tmp_path: Path) -> None:
        """Test that lowercase tickers are converted to uppercase."""
        cache = create_populated_cache(tmp_path)

        with patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache):
            result = await get_material_info("bse")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert decoded["Ticker"] == "BSE"  # type: ignore[index]

    async def test_material_not_found(self, tmp_path: Path) -> None:
        """Test material not found returns error content."""
        cache = create_populated_cache(tmp_path)

        with patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache):
            result = await get_material_info("NOTEXIST")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not found" in result[0].text.lower()

    async def test_api_error_returns_error_content(self) -> None:
        """Test FIO API error returns error content."""
        mock_cache = MagicMock(spec=MaterialsCache)
        mock_cache.is_valid.return_value = False

        mock_client = AsyncMock()
        mock_client.get_all_materials_csv.side_effect = FIOApiError(
            "Server error", status_code=500
        )

        with (
            patch(
                "prun_mcp.tools.materials.get_materials_cache", return_value=mock_cache
            ),
            patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client),
        ):
            result = await get_material_info("BSE")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text

    async def test_populates_cache_on_miss(self, tmp_path: Path) -> None:
        """Test that cache is populated when invalid."""
        cache = MaterialsCache(cache_dir=tmp_path)
        assert not cache.is_valid()

        mock_client = AsyncMock()
        mock_client.get_all_materials_csv.return_value = SAMPLE_CSV

        with (
            patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache),
            patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client),
        ):
            result = await get_material_info("BSE")

        assert isinstance(result, str)
        mock_client.get_all_materials_csv.assert_called_once()
        assert cache.is_valid()


class TestRefreshMaterialsCache:
    """Tests for refresh_materials_cache tool."""

    async def test_refresh_success(self, tmp_path: Path) -> None:
        """Test successful cache refresh."""
        cache = MaterialsCache(cache_dir=tmp_path)

        mock_client = AsyncMock()
        mock_client.get_all_materials_csv.return_value = SAMPLE_CSV

        with (
            patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache),
            patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client),
        ):
            result = await refresh_materials_cache()

        assert "refreshed" in result.lower()
        assert "2" in result  # 2 materials in SAMPLE_CSV
        mock_client.get_all_materials_csv.assert_called_once()

    async def test_refresh_invalidates_first(self, tmp_path: Path) -> None:
        """Test that refresh invalidates cache before fetching."""
        # Pre-populate cache with old data
        cache = MaterialsCache(cache_dir=tmp_path)
        cache.refresh("Ticker,Name\nOLD,oldMaterial")

        mock_client = AsyncMock()
        mock_client.get_all_materials_csv.return_value = SAMPLE_CSV

        with (
            patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache),
            patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client),
        ):
            await refresh_materials_cache()

        # Cache should now have new data
        assert cache.get_material("BSE") is not None
        assert cache.get_material("OLD") is None

    async def test_refresh_api_error(self, tmp_path: Path) -> None:
        """Test refresh handles API errors gracefully."""
        cache = MaterialsCache(cache_dir=tmp_path)

        mock_client = AsyncMock()
        mock_client.get_all_materials_csv.side_effect = FIOApiError(
            "Server error", status_code=500
        )

        with (
            patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache),
            patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client),
        ):
            result = await refresh_materials_cache()

        assert "failed" in result.lower()
