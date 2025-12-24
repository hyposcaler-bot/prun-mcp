"""Tests for material tools."""

from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import TextContent
from toon_format import decode as toon_decode

from prun_mcp.fio import FIOApiError, FIONotFoundError
from prun_mcp.tools.materials import get_material_info
from tests.conftest import SAMPLE_MATERIAL_BSE


pytestmark = pytest.mark.anyio


async def test_get_material_info_success() -> None:
    """Test successful material info fetch returns TOON-encoded data."""
    mock_client = AsyncMock()
    mock_client.get_material.return_value = SAMPLE_MATERIAL_BSE

    with patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client):
        result = await get_material_info("BSE")

    # Result should be TOON-encoded string
    assert isinstance(result, str)

    # Decode and verify content
    decoded = toon_decode(result)
    assert isinstance(decoded, dict)
    assert decoded["Ticker"] == "BSE"  # type: ignore[index]
    assert decoded["Name"] == "basicStructuralElements"  # type: ignore[index]

    # Verify client was called with uppercase ticker
    mock_client.get_material.assert_called_once_with("BSE")


async def test_get_material_info_lowercase_ticker() -> None:
    """Test that lowercase tickers are converted to uppercase."""
    mock_client = AsyncMock()
    mock_client.get_material.return_value = SAMPLE_MATERIAL_BSE

    with patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client):
        await get_material_info("bse")

    mock_client.get_material.assert_called_once_with("BSE")


async def test_get_material_info_not_found() -> None:
    """Test material not found returns error content."""
    mock_client = AsyncMock()
    mock_client.get_material.side_effect = FIONotFoundError("Material", "NOTEXIST")

    with patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client):
        result = await get_material_info("NOTEXIST")

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "not found" in result[0].text


async def test_get_material_info_api_error() -> None:
    """Test API error returns error content."""
    mock_client = AsyncMock()
    mock_client.get_material.side_effect = FIOApiError("Server error", status_code=500)

    with patch("prun_mcp.tools.materials.get_fio_client", return_value=mock_client):
        result = await get_material_info("BSE")

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "FIO API error" in result[0].text
