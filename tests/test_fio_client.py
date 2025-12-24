"""Tests for FIO API client."""

import httpx
import pytest

from prun_mcp.fio import FIOApiError, FIOClient, FIONotFoundError
from prun_mcp.fio.client import FIO_BASE_URL
from tests.conftest import (
    SAMPLE_BUILDINGS,
    SAMPLE_MATERIAL_BSE,
    SAMPLE_MATERIALS,
    MockTransport,
)


pytestmark = pytest.mark.anyio


async def test_get_material_success(mock_fio_success_transport: MockTransport) -> None:
    """Test successful material fetch."""
    async with httpx.AsyncClient(
        transport=mock_fio_success_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        result = await client.get_material("BSE")

        assert result == SAMPLE_MATERIAL_BSE
        assert result["Ticker"] == "BSE"
        assert result["Name"] == "basicStructuralElements"


async def test_get_material_not_found(
    mock_fio_not_found_transport: MockTransport,
) -> None:
    """Test material not found (204 response)."""
    async with httpx.AsyncClient(
        transport=mock_fio_not_found_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIONotFoundError) as exc_info:
            await client.get_material("NOTEXIST")

        assert exc_info.value.resource_type == "Material"
        assert exc_info.value.identifier == "NOTEXIST"
        assert exc_info.value.status_code == 204


async def test_get_material_api_error(mock_fio_error_transport: MockTransport) -> None:
    """Test API error (500 response)."""
    async with httpx.AsyncClient(
        transport=mock_fio_error_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIOApiError) as exc_info:
            await client.get_material("BSE")

        assert exc_info.value.status_code == 500


async def test_get_material_network_error() -> None:
    """Test network error handling."""

    def error_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection failed")

    transport = httpx.MockTransport(error_handler)

    async with httpx.AsyncClient(
        transport=transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIOApiError) as exc_info:
            await client.get_material("BSE")

        assert "HTTP error" in str(exc_info.value)


async def test_get_all_materials_success(
    mock_fio_success_transport: MockTransport,
) -> None:
    """Test successful fetch of all materials."""
    async with httpx.AsyncClient(
        transport=mock_fio_success_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        result = await client.get_all_materials()

        assert result == SAMPLE_MATERIALS
        assert len(result) == 3
        assert result[0]["Ticker"] == "BSE"


async def test_get_all_materials_api_error(
    mock_fio_error_transport: MockTransport,
) -> None:
    """Test API error when fetching all materials."""
    async with httpx.AsyncClient(
        transport=mock_fio_error_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIOApiError) as exc_info:
            await client.get_all_materials()

        assert exc_info.value.status_code == 500


async def test_get_all_buildings_success(
    mock_fio_buildings_transport: MockTransport,
) -> None:
    """Test successful fetch of all buildings."""
    async with httpx.AsyncClient(
        transport=mock_fio_buildings_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        result = await client.get_all_buildings()

        assert result == SAMPLE_BUILDINGS
        assert len(result) == 3
        assert result[0]["Ticker"] == "PP1"
        assert "BuildingCosts" in result[0]
        assert "Recipes" in result[0]


async def test_get_all_buildings_api_error() -> None:
    """Test API error when fetching all buildings."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/building/allbuildings":
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(404, text="Not found")

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIOApiError) as exc_info:
            await client.get_all_buildings()

        assert exc_info.value.status_code == 500
