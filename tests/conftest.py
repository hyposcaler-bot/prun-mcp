"""Shared test fixtures."""

import pytest
import httpx


# Sample material response from FIO API
SAMPLE_MATERIAL_BSE = {
    "MaterialId": "4fca6f5b5e6c5b8f6c5d4e3f2a1b0c9d",
    "CategoryName": "construction prefabs",
    "CategoryId": "category-123",
    "Name": "basicStructuralElements",
    "Ticker": "BSE",
    "Weight": 0.3,
    "Volume": 0.5,
}


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
    """Transport that returns successful material response."""
    return create_mock_transport(
        {
            "/material/BSE": httpx.Response(200, json=SAMPLE_MATERIAL_BSE),
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
        }
    )
