"""Tests for FIO API client."""

import httpx
import pytest

from prun_mcp.fio import FIOApiError, FIOClient, FIONotFoundError
from prun_mcp.fio.client import FIO_BASE_URL
from tests.conftest import (
    SAMPLE_BUILDINGS,
    SAMPLE_EXCHANGE_ALL,
    SAMPLE_EXCHANGE_RAT_CI1,
    SAMPLE_MATERIAL_BSE,
    SAMPLE_MATERIALS,
    SAMPLE_PLANET_KATOA,
    SAMPLE_RECIPES,
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


async def test_get_planet_success(
    mock_fio_planet_success_transport: MockTransport,
) -> None:
    """Test successful planet fetch by name."""
    async with httpx.AsyncClient(
        transport=mock_fio_planet_success_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        result = await client.get_planet("Katoa")

        assert result == SAMPLE_PLANET_KATOA
        assert result["PlanetName"] == "Katoa"
        assert result["PlanetNaturalId"] == "XK-745b"


async def test_get_planet_by_natural_id(
    mock_fio_planet_success_transport: MockTransport,
) -> None:
    """Test successful planet fetch by natural ID."""
    async with httpx.AsyncClient(
        transport=mock_fio_planet_success_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        result = await client.get_planet("XK-745b")

        assert result["PlanetName"] == "Katoa"


async def test_get_planet_not_found(
    mock_fio_planet_not_found_transport: MockTransport,
) -> None:
    """Test planet not found (204 response)."""
    async with httpx.AsyncClient(
        transport=mock_fio_planet_not_found_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIONotFoundError) as exc_info:
            await client.get_planet("NOTEXIST")

        assert exc_info.value.resource_type == "Planet"
        assert exc_info.value.identifier == "NOTEXIST"
        assert exc_info.value.status_code == 204


async def test_get_planet_api_error() -> None:
    """Test API error when fetching planet."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/planet/Katoa":
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(404, text="Not found")

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIOApiError) as exc_info:
            await client.get_planet("Katoa")

        assert exc_info.value.status_code == 500


async def test_get_planet_network_error() -> None:
    """Test network error handling for planet fetch."""

    def error_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection failed")

    transport = httpx.MockTransport(error_handler)

    async with httpx.AsyncClient(
        transport=transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIOApiError) as exc_info:
            await client.get_planet("Katoa")

        assert "HTTP error" in str(exc_info.value)


async def test_get_all_recipes_success(
    mock_fio_recipes_transport: MockTransport,
) -> None:
    """Test successful fetch of all recipes."""
    async with httpx.AsyncClient(
        transport=mock_fio_recipes_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        result = await client.get_all_recipes()

        assert result == SAMPLE_RECIPES
        assert len(result) == 5
        assert result[0]["BuildingTicker"] == "PP1"
        assert "Inputs" in result[0]
        assert "Outputs" in result[0]


async def test_get_all_recipes_api_error() -> None:
    """Test API error when fetching all recipes."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recipes/allrecipes":
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(404, text="Not found")

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIOApiError) as exc_info:
            await client.get_all_recipes()

        assert exc_info.value.status_code == 500


async def test_get_all_recipes_network_error() -> None:
    """Test network error handling for recipes fetch."""

    def error_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection failed")

    transport = httpx.MockTransport(error_handler)

    async with httpx.AsyncClient(
        transport=transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIOApiError) as exc_info:
            await client.get_all_recipes()

        assert "HTTP error" in str(exc_info.value)


async def test_get_exchange_info_success(
    mock_fio_exchange_success_transport: MockTransport,
) -> None:
    """Test successful exchange info fetch."""
    async with httpx.AsyncClient(
        transport=mock_fio_exchange_success_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        result = await client.get_exchange_info("RAT", "CI1")

        assert result == SAMPLE_EXCHANGE_RAT_CI1
        assert result["MaterialTicker"] == "RAT"
        assert result["ExchangeCode"] == "CI1"
        assert "BuyingOrders" in result
        assert "SellingOrders" in result


async def test_get_exchange_info_not_found(
    mock_fio_exchange_not_found_transport: MockTransport,
) -> None:
    """Test exchange not found (204 response)."""
    async with httpx.AsyncClient(
        transport=mock_fio_exchange_not_found_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIONotFoundError) as exc_info:
            await client.get_exchange_info("INVALID", "CI1")

        assert exc_info.value.resource_type == "Exchange"
        assert exc_info.value.identifier == "INVALID.CI1"
        assert exc_info.value.status_code == 204


async def test_get_exchange_info_api_error() -> None:
    """Test API error when fetching exchange info."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/exchange/RAT.CI1":
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(404, text="Not found")

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIOApiError) as exc_info:
            await client.get_exchange_info("RAT", "CI1")

        assert exc_info.value.status_code == 500


async def test_get_exchange_info_network_error() -> None:
    """Test network error handling for exchange fetch."""

    def error_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection failed")

    transport = httpx.MockTransport(error_handler)

    async with httpx.AsyncClient(
        transport=transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIOApiError) as exc_info:
            await client.get_exchange_info("RAT", "CI1")

        assert "HTTP error" in str(exc_info.value)


async def test_get_all_exchange_data_success(
    mock_fio_exchange_success_transport: MockTransport,
) -> None:
    """Test successful fetch of all exchange data."""
    async with httpx.AsyncClient(
        transport=mock_fio_exchange_success_transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        result = await client.get_all_exchange_data()

        assert result == SAMPLE_EXCHANGE_ALL
        assert len(result) == 3
        assert result[0]["MaterialTicker"] == "RAT"
        assert result[0]["ExchangeCode"] == "CI1"


async def test_get_all_exchange_data_api_error() -> None:
    """Test API error when fetching all exchange data."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/exchange/all":
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(404, text="Not found")

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIOApiError) as exc_info:
            await client.get_all_exchange_data()

        assert exc_info.value.status_code == 500


async def test_get_all_exchange_data_network_error() -> None:
    """Test network error handling for all exchange data fetch."""

    def error_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection failed")

    transport = httpx.MockTransport(error_handler)

    async with httpx.AsyncClient(
        transport=transport, base_url=FIO_BASE_URL
    ) as http_client:
        client = FIOClient()
        client._client = http_client

        with pytest.raises(FIOApiError) as exc_info:
            await client.get_all_exchange_data()

        assert "HTTP error" in str(exc_info.value)


# ===== Price Cache Tests =====


class TestPriceCache:
    """Tests for in-memory price caching."""

    async def test_exchange_info_cache_hit(self) -> None:
        """Second call returns cached data without HTTP request."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json=SAMPLE_EXCHANGE_RAT_CI1)

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport, base_url=FIO_BASE_URL
        ) as http_client:
            client = FIOClient()
            client._client = http_client

            # First call - should hit the network
            result1 = await client.get_exchange_info("RAT", "CI1")
            assert call_count == 1
            assert result1 == SAMPLE_EXCHANGE_RAT_CI1

            # Second call - should use cache
            result2 = await client.get_exchange_info("RAT", "CI1")
            assert call_count == 1  # No additional HTTP call
            assert result2 == SAMPLE_EXCHANGE_RAT_CI1

    async def test_exchange_info_cache_miss_after_ttl(self) -> None:
        """Expired cache triggers new fetch."""
        import time
        from unittest.mock import patch

        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json=SAMPLE_EXCHANGE_RAT_CI1)

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport, base_url=FIO_BASE_URL
        ) as http_client:
            client = FIOClient()
            client._client = http_client

            # First call
            await client.get_exchange_info("RAT", "CI1")
            assert call_count == 1

            # Simulate time passing beyond TTL
            with patch.object(time, "time", return_value=time.time() + 200):
                await client.get_exchange_info("RAT", "CI1")
                assert call_count == 2  # New fetch after TTL expired

    async def test_exchange_all_cache_hit(self) -> None:
        """get_all_exchange_data caches results."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json=SAMPLE_EXCHANGE_ALL)

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport, base_url=FIO_BASE_URL
        ) as http_client:
            client = FIOClient()
            client._client = http_client

            # First call
            result1 = await client.get_all_exchange_data()
            assert call_count == 1
            assert result1 == SAMPLE_EXCHANGE_ALL

            # Second call - should use cache
            result2 = await client.get_all_exchange_data()
            assert call_count == 1  # No additional HTTP call
            assert result2 == SAMPLE_EXCHANGE_ALL

    async def test_cache_keys_are_distinct(self) -> None:
        """Different tickers/exchanges have separate cache entries."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            # Return different data based on path
            path = request.url.path
            data = dict(SAMPLE_EXCHANGE_RAT_CI1)
            if "COF" in path:
                data["MaterialTicker"] = "COF"
            if "NC1" in path:
                data["ExchangeCode"] = "NC1"
            return httpx.Response(200, json=data)

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport, base_url=FIO_BASE_URL
        ) as http_client:
            client = FIOClient()
            client._client = http_client

            # Different ticker - separate cache
            await client.get_exchange_info("RAT", "CI1")
            await client.get_exchange_info("COF", "CI1")
            assert call_count == 2

            # Different exchange - separate cache
            await client.get_exchange_info("RAT", "NC1")
            assert call_count == 3

            # Same ticker/exchange - use cache
            await client.get_exchange_info("RAT", "CI1")
            assert call_count == 3  # No additional call
