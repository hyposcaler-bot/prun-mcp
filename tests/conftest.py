"""Shared test fixtures."""

import pytest
import httpx


# Sample material response from FIO API (JSON format)
SAMPLE_MATERIAL_BSE = {
    "MaterialId": "4fca6f5b5e6c5b8f6c5d4e3f2a1b0c9d",
    "CategoryName": "construction prefabs",
    "CategoryId": "category-123",
    "Name": "basicStructuralElements",
    "Ticker": "BSE",
    "Weight": 0.3,
    "Volume": 0.5,
}

# Sample CSV content from FIO API
SAMPLE_MATERIALS_CSV = """Ticker,Name,CategoryName,Weight,Volume
BSE,basicStructuralElements,construction prefabs,0.3,0.5
RAT,rations,consumables (basic),0.21,0.1
H2O,water,consumables (basic),0.1,0.1
"""


class MockTransport(httpx.MockTransport):
    """Custom mock transport for testing."""

    pass


def create_mock_transport(responses: dict[str, httpx.Response]) -> MockTransport:
    """Create a mock transport with predefined responses.

    Args:
        responses: Dict mapping URL paths to Response objects

    Returns:
        MockTransport configured with the responses
    """

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in responses:
            return responses[path]
        return httpx.Response(404, text="Not found")

    return MockTransport(handler)


@pytest.fixture
def mock_fio_success_transport() -> MockTransport:
    """Transport that returns successful responses for material endpoints."""
    return create_mock_transport(
        {
            "/material/BSE": httpx.Response(200, json=SAMPLE_MATERIAL_BSE),
            "/csv/materials": httpx.Response(200, text=SAMPLE_MATERIALS_CSV),
        }
    )


@pytest.fixture
def mock_fio_not_found_transport() -> MockTransport:
    """Transport that returns 204 for material not found."""
    return create_mock_transport(
        {
            "/material/NOTEXIST": httpx.Response(204),
        }
    )


@pytest.fixture
def mock_fio_error_transport() -> MockTransport:
    """Transport that returns 500 error."""
    return create_mock_transport(
        {
            "/material/BSE": httpx.Response(500, text="Internal Server Error"),
            "/csv/materials": httpx.Response(500, text="Internal Server Error"),
        }
    )
