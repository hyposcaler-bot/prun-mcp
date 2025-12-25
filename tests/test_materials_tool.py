"""Tests for material tools."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent
from toon_format import decode as toon_decode

from prun_mcp.cache import MaterialsCache
from prun_mcp.fio import FIOApiError
from prun_mcp.tools.materials import (
    get_all_materials,
    get_material_info,
    refresh_materials_cache,
)

from tests.conftest import SAMPLE_MATERIALS


pytestmark = pytest.mark.anyio


def create_populated_cache(tmp_path: Path) -> MaterialsCache:
    """Create a cache populated with sample data."""
    cache = MaterialsCache(cache_dir=tmp_path)
    cache.refresh(SAMPLE_MATERIALS)
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
        assert "materials" in decoded  # type: ignore[operator]

        materials = decoded["materials"]  # type: ignore[index]
        assert len(materials) == 1

        material = materials[0]
        assert material["Ticker"] == "BSE"
        assert material["Name"] == "basicStructuralElements"

    async def test_lowercase_ticker_converted(self, tmp_path: Path) -> None:
        """Test that lowercase tickers are converted to uppercase."""
        cache = create_populated_cache(tmp_path)

        with patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache):
            result = await get_material_info("bse")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        materials = decoded["materials"]  # type: ignore[index]
        assert materials[0]["Ticker"] == "BSE"  # type: ignore[index]

    async def test_multiple_tickers(self, tmp_path: Path) -> None:
        """Test comma-separated tickers returns multiple materials."""
        cache = create_populated_cache(tmp_path)

        with patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache):
            result = await get_material_info("BSE,RAT,H2O")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        materials = decoded["materials"]  # type: ignore[index]
        assert len(materials) == 3

        tickers = [m["Ticker"] for m in materials]  # type: ignore[index]
        assert "BSE" in tickers
        assert "RAT" in tickers
        assert "H2O" in tickers

    async def test_multiple_tickers_with_spaces(self, tmp_path: Path) -> None:
        """Test comma-separated tickers with spaces are handled."""
        cache = create_populated_cache(tmp_path)

        with patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache):
            result = await get_material_info("BSE, RAT, H2O")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        materials = decoded["materials"]  # type: ignore[index]
        assert len(materials) == 3

    async def test_partial_match_includes_not_found(self, tmp_path: Path) -> None:
        """Test partial matches return found materials plus not_found list."""
        cache = create_populated_cache(tmp_path)

        with patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache):
            result = await get_material_info("BSE,INVALID,RAT")

        assert isinstance(result, str)
        decoded = toon_decode(result)

        # Should have found materials
        materials = decoded["materials"]  # type: ignore[index]
        assert len(materials) == 2
        tickers = [m["Ticker"] for m in materials]  # type: ignore[index]
        assert "BSE" in tickers
        assert "RAT" in tickers

        # Should have not_found list
        not_found = decoded["not_found"]  # type: ignore[index]
        assert "INVALID" in not_found

    async def test_all_not_found(self, tmp_path: Path) -> None:
        """Test all materials not found returns error content."""
        cache = create_populated_cache(tmp_path)

        with patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache):
            result = await get_material_info("INVALID1,INVALID2")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not found" in result[0].text.lower()
        assert "INVALID1" in result[0].text
        assert "INVALID2" in result[0].text

    async def test_api_error_returns_error_content(self) -> None:
        """Test FIO API error returns error content."""
        mock_cache = MagicMock(spec=MaterialsCache)
        mock_cache.is_valid.return_value = False

        mock_client = AsyncMock()
        mock_client.get_all_materials.side_effect = FIOApiError(
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
        mock_client.get_all_materials.return_value = SAMPLE_MATERIALS

        with (
            patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache),
            patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client),
        ):
            result = await get_material_info("BSE")

        assert isinstance(result, str)
        mock_client.get_all_materials.assert_called_once()
        assert cache.is_valid()

    async def test_lookup_by_material_id(self, tmp_path: Path) -> None:
        """Test lookup by MaterialId returns correct data."""
        cache = create_populated_cache(tmp_path)

        with patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache):
            # BSE has MaterialId "4fca6f5b5e6c5b8f6c5d4e3f2a1b0c9d"
            result = await get_material_info("4fca6f5b5e6c5b8f6c5d4e3f2a1b0c9d")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        materials = decoded["materials"]  # type: ignore[index]
        assert len(materials) == 1
        assert materials[0]["Ticker"] == "BSE"  # type: ignore[index]

    async def test_lookup_by_id_matches_ticker_lookup(self, tmp_path: Path) -> None:
        """Test round-trip: lookup by ID, get ticker, lookup by ticker matches."""
        cache = create_populated_cache(tmp_path)

        with patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache):
            # Step 1: Look up by MaterialId
            result_by_id = await get_material_info("4fca6f5b5e6c5b8f6c5d4e3f2a1b0c9d")
            assert isinstance(result_by_id, str)
            decoded_by_id = toon_decode(result_by_id)
            materials_by_id = decoded_by_id["materials"]  # type: ignore[index]

            # Step 2: Extract the Ticker
            ticker = materials_by_id[0]["Ticker"]  # type: ignore[index]
            assert ticker == "BSE"

            # Step 3: Look up by Ticker
            result_by_ticker = await get_material_info(ticker)
            assert isinstance(result_by_ticker, str)
            decoded_by_ticker = toon_decode(result_by_ticker)
            materials_by_ticker = decoded_by_ticker["materials"]  # type: ignore[index]

            # Step 4: Verify both return the same data
            assert materials_by_id[0] == materials_by_ticker[0]  # type: ignore[index]


class TestRefreshMaterialsCache:
    """Tests for refresh_materials_cache tool."""

    async def test_refresh_success(self, tmp_path: Path) -> None:
        """Test successful cache refresh."""
        cache = MaterialsCache(cache_dir=tmp_path)

        mock_client = AsyncMock()
        mock_client.get_all_materials.return_value = SAMPLE_MATERIALS

        with (
            patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache),
            patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client),
        ):
            result = await refresh_materials_cache()

        assert "refreshed" in result.lower()
        assert "3" in result  # 3 materials in SAMPLE_MATERIALS
        mock_client.get_all_materials.assert_called_once()

    async def test_refresh_invalidates_first(self, tmp_path: Path) -> None:
        """Test that refresh invalidates cache before fetching."""
        # Pre-populate cache with old data
        cache = MaterialsCache(cache_dir=tmp_path)
        cache.refresh([{"Ticker": "OLD", "Name": "oldMaterial"}])

        mock_client = AsyncMock()
        mock_client.get_all_materials.return_value = SAMPLE_MATERIALS

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
        mock_client.get_all_materials.side_effect = FIOApiError(
            "Server error", status_code=500
        )

        with (
            patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache),
            patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client),
        ):
            result = await refresh_materials_cache()

        assert "failed" in result.lower()


class TestGetAllMaterials:
    """Tests for get_all_materials tool."""

    async def test_returns_toon_encoded_list(self, tmp_path: Path) -> None:
        """Test that get_all_materials returns TOON-encoded list."""
        cache = create_populated_cache(tmp_path)

        with patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache):
            result = await get_all_materials()

        assert isinstance(result, str)

        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        assert "materials" in decoded
        materials = decoded["materials"]
        assert len(materials) == 3

        tickers = [m["Ticker"] for m in materials]  # type: ignore[index]
        assert "BSE" in tickers
        assert "RAT" in tickers
        assert "H2O" in tickers

    async def test_populates_cache_on_miss(self, tmp_path: Path) -> None:
        """Test that cache is populated when invalid."""
        cache = MaterialsCache(cache_dir=tmp_path)
        assert not cache.is_valid()

        mock_client = AsyncMock()
        mock_client.get_all_materials.return_value = SAMPLE_MATERIALS

        with (
            patch("prun_mcp.tools.materials.get_materials_cache", return_value=cache),
            patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client),
        ):
            result = await get_all_materials()

        assert isinstance(result, str)
        mock_client.get_all_materials.assert_called_once()
        assert cache.is_valid()

    async def test_api_error_returns_error_content(self) -> None:
        """Test FIO API error returns error content."""
        mock_cache = MagicMock(spec=MaterialsCache)
        mock_cache.is_valid.return_value = False

        mock_client = AsyncMock()
        mock_client.get_all_materials.side_effect = FIOApiError(
            "Server error", status_code=500
        )

        with (
            patch(
                "prun_mcp.tools.materials.get_materials_cache", return_value=mock_cache
            ),
            patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client),
        ):
            result = await get_all_materials()

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text
