"""Tests for FIO Pydantic models."""

from prun_mcp.models.fio import (
    FIOBuilding,
    FIOBuildingCost,
    FIOBuildingFull,
    FIOExchangeOrder,
    FIOMaterial,
    camel_to_title,
)


class TestCamelToTitle:
    """Tests for camel_to_title function."""

    def test_simple_camel_case(self) -> None:
        """Test basic camelCase conversion."""
        assert camel_to_title("drinkingWater") == "Drinking Water"

    def test_multiple_words(self) -> None:
        """Test camelCase with multiple words."""
        assert camel_to_title("pioneerClothing") == "Pioneer Clothing"
        assert camel_to_title("advancedFuelRod") == "Advanced Fuel Rod"

    def test_single_word(self) -> None:
        """Test single word is just title-cased."""
        assert camel_to_title("aluminium") == "Aluminium"
        assert camel_to_title("water") == "Water"

    def test_already_title_case(self) -> None:
        """Test already title-cased strings are handled."""
        assert camel_to_title("Basic Material") == "Basic Material"

    def test_empty_string(self) -> None:
        """Test empty string returns empty."""
        assert camel_to_title("") == ""

    def test_consecutive_uppercase(self) -> None:
        """Test strings with consecutive uppercase letters."""
        # This is edge case behavior - consecutive caps stay together
        assert camel_to_title("FIOClient") == "Fioclient"

    def test_with_numbers(self) -> None:
        """Test strings containing numbers - numbers don't create word breaks."""
        assert camel_to_title("hb1") == "Hb1"
        # Numbers don't trigger word breaks (only lowercase->uppercase does)
        assert camel_to_title("type2Building") == "Type2Building"


class TestFIOMaterialPrettification:
    """Tests for FIOMaterial name prettification."""

    def test_name_prettified(self) -> None:
        """Test that Name field is prettified."""
        data = {
            "MaterialId": "123",
            "Name": "drinkingWater",
            "Ticker": "DW",
        }
        material = FIOMaterial.model_validate(data)
        assert material.name == "Drinking Water"

    def test_category_name_prettified(self) -> None:
        """Test that CategoryName field is prettified."""
        data = {
            "MaterialId": "123",
            "Name": "Water",
            "CategoryName": "consumablesBasic",
            "Ticker": "H2O",
        }
        material = FIOMaterial.model_validate(data)
        assert material.category_name == "Consumables Basic"

    def test_model_dump_preserves_prettification(self) -> None:
        """Test that model_dump with by_alias preserves prettified names."""
        data = {
            "MaterialId": "123",
            "Name": "drinkingWater",
            "Ticker": "DW",
        }
        material = FIOMaterial.model_validate(data)
        dumped = material.model_dump(by_alias=True)
        assert dumped["Name"] == "Drinking Water"


class TestFIOBuildingCostPrettification:
    """Tests for FIOBuildingCost commodity name prettification."""

    def test_commodity_name_prettified(self) -> None:
        """Test that CommodityName field is prettified."""
        data = {
            "CommodityName": "basicStructuralElements",
            "CommodityTicker": "BSE",
            "Amount": 10,
        }
        cost = FIOBuildingCost.model_validate(data)
        assert cost.commodity_name == "Basic Structural Elements"


class TestFIOBuildingPrettification:
    """Tests for FIOBuilding name prettification."""

    def test_name_prettified(self) -> None:
        """Test that Name field is prettified."""
        data = {
            "Ticker": "PP1",
            "Name": "prefabPlant",
            "AreaCost": 30,
        }
        building = FIOBuilding.model_validate(data)
        assert building.name == "Prefab Plant"


class TestFIOBuildingFullPrettification:
    """Tests for FIOBuildingFull name prettification."""

    def test_name_prettified(self) -> None:
        """Test that Name field is prettified."""
        data = {
            "Ticker": "FP",
            "Name": "foodProcessor",
            "AreaCost": 25,
        }
        building = FIOBuildingFull.model_validate(data)
        assert building.name == "Food Processor"

    def test_nested_building_costs_prettified(self) -> None:
        """Test that nested BuildingCosts have prettified names."""
        data = {
            "Ticker": "PP1",
            "Name": "prefabPlant1",
            "AreaCost": 30,
            "BuildingCosts": [
                {
                    "CommodityName": "basicStructuralElements",
                    "CommodityTicker": "BSE",
                    "Amount": 4,
                },
                {
                    "CommodityName": "mineralConstructionGranulate",
                    "CommodityTicker": "MCG",
                    "Amount": 2,
                },
            ],
        }
        building = FIOBuildingFull.model_validate(data)
        dumped = building.model_dump(by_alias=True)
        assert (
            dumped["BuildingCosts"][0]["CommodityName"] == "Basic Structural Elements"
        )
        assert (
            dumped["BuildingCosts"][1]["CommodityName"]
            == "Mineral Construction Granulate"
        )


class TestFIOExchangeOrder:
    """Tests for FIOExchangeOrder handling of nullable fields."""

    def test_with_all_fields(self) -> None:
        """Test order with all fields populated."""
        data = {
            "CompanyCode": "TEST",
            "ItemCount": 100,
            "ItemCost": 50.0,
        }
        order = FIOExchangeOrder.model_validate(data)
        assert order.company_code == "TEST"
        assert order.item_count == 100
        assert order.item_cost == 50.0

    def test_with_null_item_count(self) -> None:
        """Test order with null ItemCount (market maker orders)."""
        data = {
            "CompanyCode": "CIMM",
            "ItemCount": None,
            "ItemCost": 176.0,
        }
        order = FIOExchangeOrder.model_validate(data)
        assert order.company_code == "CIMM"
        assert order.item_count is None
        assert order.item_cost == 176.0

    def test_with_null_item_cost(self) -> None:
        """Test order with null ItemCost."""
        data = {
            "CompanyCode": "TEST",
            "ItemCount": 100,
            "ItemCost": None,
        }
        order = FIOExchangeOrder.model_validate(data)
        assert order.item_cost is None

    def test_missing_optional_fields_default_to_none(self) -> None:
        """Test that missing optional fields default to None."""
        data = {
            "CompanyCode": "TEST",
        }
        order = FIOExchangeOrder.model_validate(data)
        assert order.item_count is None
        assert order.item_cost is None
