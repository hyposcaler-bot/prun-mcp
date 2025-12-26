"""Tests for utility functions."""

from prun_mcp.utils import camel_to_title, prettify_names


class TestCamelToTitle:
    """Tests for camel_to_title function."""

    def test_single_word(self) -> None:
        """Test single word conversion."""
        assert camel_to_title("aluminium") == "Aluminium"
        assert camel_to_title("water") == "Water"

    def test_two_words(self) -> None:
        """Test two word camelCase conversion."""
        assert camel_to_title("drinkingWater") == "Drinking Water"
        assert camel_to_title("ironOre") == "Iron Ore"

    def test_three_words(self) -> None:
        """Test three word camelCase conversion."""
        assert camel_to_title("basicStructuralElements") == "Basic Structural Elements"
        assert camel_to_title("advancedFuelRod") == "Advanced Fuel Rod"

    def test_many_words(self) -> None:
        """Test multi-word camelCase conversion."""
        assert camel_to_title("pioneerLuxuryDrink") == "Pioneer Luxury Drink"
        assert camel_to_title("advancedThermalProtectionMaterial") == "Advanced Thermal Protection Material"

    def test_empty_string(self) -> None:
        """Test empty string."""
        assert camel_to_title("") == ""

    def test_already_capitalized(self) -> None:
        """Test string that starts with uppercase."""
        # Title case will normalize it
        assert camel_to_title("DrinkingWater") == "Drinking Water"


class TestPrettifyNames:
    """Tests for prettify_names function."""

    def test_simple_dict(self) -> None:
        """Test simple dict with Name field."""
        data = {"Name": "drinkingWater", "Ticker": "DW"}
        result = prettify_names(data)
        assert result == {"Name": "Drinking Water", "Ticker": "DW"}

    def test_category_name(self) -> None:
        """Test CategoryName field transformation."""
        data = {"Name": "rations", "CategoryName": "consumables"}
        result = prettify_names(data)
        assert result == {"Name": "Rations", "CategoryName": "Consumables"}

    def test_material_name(self) -> None:
        """Test MaterialName field transformation."""
        data = {"MaterialName": "drinkingWater", "Price": 100}
        result = prettify_names(data)
        assert result == {"MaterialName": "Drinking Water", "Price": 100}

    def test_commodity_name(self) -> None:
        """Test CommodityName field transformation."""
        data = {"CommodityName": "basicStructuralElements", "Amount": 5}
        result = prettify_names(data)
        assert result == {"CommodityName": "Basic Structural Elements", "Amount": 5}

    def test_nested_dict(self) -> None:
        """Test nested dict with Name fields at multiple levels."""
        data = {
            "Name": "foodProcessor",
            "BuildingCosts": [
                {"CommodityName": "basicBulkhead", "Amount": 3},
                {"CommodityName": "basicDeckElements", "Amount": 3},
            ],
        }
        result = prettify_names(data)
        assert result == {
            "Name": "Food Processor",
            "BuildingCosts": [
                {"CommodityName": "Basic Bulkhead", "Amount": 3},
                {"CommodityName": "Basic Deck Elements", "Amount": 3},
            ],
        }

    def test_list_of_dicts(self) -> None:
        """Test list of dicts with Name fields."""
        data = [
            {"Name": "water", "Ticker": "H2O"},
            {"Name": "drinkingWater", "Ticker": "DW"},
        ]
        result = prettify_names(data)
        assert result == [
            {"Name": "Water", "Ticker": "H2O"},
            {"Name": "Drinking Water", "Ticker": "DW"},
        ]

    def test_primitive_passthrough(self) -> None:
        """Test that primitive values pass through unchanged."""
        assert prettify_names("hello") == "hello"
        assert prettify_names(123) == 123
        assert prettify_names(None) is None
        assert prettify_names(True) is True

    def test_empty_structures(self) -> None:
        """Test empty dict and list."""
        assert prettify_names({}) == {}
        assert prettify_names([]) == []

    def test_non_name_fields_unchanged(self) -> None:
        """Test that fields not in NAME_FIELDS are unchanged."""
        data = {"Ticker": "RAT", "Weight": 0.21, "Volume": 0.1}
        result = prettify_names(data)
        assert result == {"Ticker": "RAT", "Weight": 0.21, "Volume": 0.1}

    def test_deeply_nested(self) -> None:
        """Test deeply nested structure."""
        data = {
            "materials": [
                {
                    "Name": "rations",
                    "CategoryName": "consumables",
                    "nested": {
                        "deep": {
                            "MaterialName": "proteinBeans",
                        }
                    },
                }
            ]
        }
        result = prettify_names(data)
        assert result == {
            "materials": [
                {
                    "Name": "Rations",
                    "CategoryName": "Consumables",
                    "nested": {
                        "deep": {
                            "MaterialName": "Protein Beans",
                        }
                    },
                }
            ]
        }

    def test_all_name_fields(self) -> None:
        """Test all four NAME_FIELDS are transformed."""
        data = {
            "Name": "testName",
            "CategoryName": "testCategory",
            "MaterialName": "testMaterial",
            "CommodityName": "testCommodity",
        }
        result = prettify_names(data)
        assert result == {
            "Name": "Test Name",
            "CategoryName": "Test Category",
            "MaterialName": "Test Material",
            "CommodityName": "Test Commodity",
        }
