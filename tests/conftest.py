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

# Sample materials list from /material/allmaterials
SAMPLE_MATERIALS = [
    {
        "MaterialId": "4fca6f5b5e6c5b8f6c5d4e3f2a1b0c9d",
        "CategoryName": "construction prefabs",
        "CategoryId": "category-123",
        "Name": "basicStructuralElements",
        "Ticker": "BSE",
        "Weight": 0.3,
        "Volume": 0.5,
    },
    {
        "MaterialId": "5fca6f5b5e6c5b8f6c5d4e3f2a1b0c9e",
        "CategoryName": "consumables (basic)",
        "CategoryId": "category-456",
        "Name": "rations",
        "Ticker": "RAT",
        "Weight": 0.21,
        "Volume": 0.1,
    },
    {
        "MaterialId": "6fca6f5b5e6c5b8f6c5d4e3f2a1b0c9f",
        "CategoryName": "consumables (basic)",
        "CategoryId": "category-456",
        "Name": "water",
        "Ticker": "H2O",
        "Weight": 0.1,
        "Volume": 0.1,
    },
]

# Sample buildings list from /building/allbuildings
SAMPLE_BUILDINGS = [
    {
        "BuildingId": "1d9c9787a38e11dd7f7cfec32245bb76",
        "Name": "prefabPlant1",
        "Ticker": "PP1",
        "Expertise": "CONSTRUCTION",
        "Pioneers": 80,
        "Settlers": 0,
        "Technicians": 0,
        "Engineers": 0,
        "Scientists": 0,
        "AreaCost": 19,
        "BuildingCosts": [
            {
                "CommodityName": "basicStructuralElements",
                "CommodityTicker": "BSE",
                "Amount": 4,
            },
            {"CommodityName": "basicBulkhead", "CommodityTicker": "BBH", "Amount": 3},
            {
                "CommodityName": "basicDeckElements",
                "CommodityTicker": "BDE",
                "Amount": 3,
            },
        ],
        "Recipes": [
            {
                "BuildingRecipeId": "recipe-1",
                "RecipeName": "BSE:1",
                "StandardRecipeName": "4xPE=>1xBSE",
                "DurationMs": 25920000,
                "Inputs": [{"CommodityTicker": "PE", "Amount": 4}],
                "Outputs": [{"CommodityTicker": "BSE", "Amount": 1}],
            }
        ],
    },
    {
        "BuildingId": "2d9c9787a38e11dd7f7cfec32245bb77",
        "Name": "habitationPioneer",
        "Ticker": "HB1",
        "Expertise": None,
        "Pioneers": 100,
        "Settlers": 0,
        "Technicians": 0,
        "Engineers": 0,
        "Scientists": 0,
        "AreaCost": 100,
        "BuildingCosts": [
            {
                "CommodityName": "basicStructuralElements",
                "CommodityTicker": "BSE",
                "Amount": 16,
            },
            {"CommodityName": "basicBulkhead", "CommodityTicker": "BBH", "Amount": 4},
        ],
        "Recipes": [],
    },
    {
        "BuildingId": "3d9c9787a38e11dd7f7cfec32245bb78",
        "Name": "farmstead",
        "Ticker": "FRM",
        "Expertise": "AGRICULTURE",
        "Pioneers": 80,
        "Settlers": 0,
        "Technicians": 0,
        "Engineers": 0,
        "Scientists": 0,
        "AreaCost": 40,
        "BuildingCosts": [
            {
                "CommodityName": "basicStructuralElements",
                "CommodityTicker": "BSE",
                "Amount": 4,
            },
            {"CommodityName": "basicBulkhead", "CommodityTicker": "BBH", "Amount": 2},
        ],
        "Recipes": [],
    },
]


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
            "/material/allmaterials": httpx.Response(200, json=SAMPLE_MATERIALS),
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
            "/material/allmaterials": httpx.Response(500, text="Internal Server Error"),
        }
    )


@pytest.fixture
def mock_fio_buildings_transport() -> MockTransport:
    """Transport that returns successful responses for building endpoints."""
    return create_mock_transport(
        {
            "/building/allbuildings": httpx.Response(200, json=SAMPLE_BUILDINGS),
        }
    )
