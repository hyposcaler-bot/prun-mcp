"""Pydantic models for FIO API responses.

These models represent the data returned by the FIO REST API.
They use aliases to map from the API's PascalCase to Python's snake_case.
Name fields are automatically prettified from camelCase to Title Case.
"""

import re
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field


def camel_to_title(text: str) -> str:
    """Convert camelCase to Title Case.

    Args:
        text: A camelCase string (e.g., "drinkingWater").

    Returns:
        Title Case string (e.g., "Drinking Water").

    Examples:
        >>> camel_to_title("drinkingWater")
        'Drinking Water'
        >>> camel_to_title("pioneerClothing")
        'Pioneer Clothing'
    """
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return spaced.title()


def _prettify_name(v: Any) -> Any:
    """Validator that converts camelCase strings to Title Case."""
    if isinstance(v, str) and v:
        return camel_to_title(v)
    return v


# Annotated type for name fields that auto-prettify from camelCase
PrettifiedName = Annotated[str, BeforeValidator(_prettify_name)]


class FIOMaterial(BaseModel):
    """Material data from the FIO API."""

    material_id: str = Field(alias="MaterialId")
    category_name: PrettifiedName = Field(alias="CategoryName", default="")
    category_id: str = Field(alias="CategoryId", default="")
    name: PrettifiedName = Field(alias="Name")
    ticker: str = Field(alias="Ticker")
    weight: float = Field(alias="Weight", default=0.0)
    volume: float = Field(alias="Volume", default=0.0)

    model_config = {"populate_by_name": True, "extra": "ignore"}


class FIOBuildingCost(BaseModel):
    """A single material cost entry for a building."""

    commodity_name: PrettifiedName = Field(alias="CommodityName", default="")
    commodity_ticker: str = Field(alias="CommodityTicker")
    amount: int = Field(alias="Amount")

    model_config = {"populate_by_name": True, "extra": "ignore"}


class FIOBuilding(BaseModel):
    """Building data from the FIO API.

    Contains core building information needed for cost calculations.
    Additional fields from the API are ignored.
    """

    ticker: str = Field(alias="Ticker")
    name: PrettifiedName = Field(alias="Name")
    area_cost: int = Field(alias="AreaCost")
    building_costs: list[FIOBuildingCost] = Field(
        default_factory=list, alias="BuildingCosts"
    )

    model_config = {"populate_by_name": True, "extra": "ignore"}


class FIOPlanet(BaseModel):
    """Planet data from the FIO API.

    Contains planetary environment information needed for infrastructure
    cost calculations. Additional fields from the API are ignored.
    """

    planet_name: str = Field(alias="PlanetName")
    planet_natural_id: str = Field(alias="PlanetNaturalId")
    surface: bool = Field(alias="Surface", default=True)
    pressure: float = Field(alias="Pressure", default=1.0)
    gravity: float = Field(alias="Gravity", default=1.0)
    temperature: float = Field(alias="Temperature", default=20.0)
    fertility: float | None = Field(alias="Fertility", default=None)

    model_config = {"populate_by_name": True, "extra": "ignore"}


class FIORecipeIO(BaseModel):
    """Input or output of a recipe."""

    ticker: str = Field(alias="Ticker")
    amount: int = Field(alias="Amount")

    model_config = {"populate_by_name": True}


class FIORecipe(BaseModel):
    """Recipe data from the FIO API."""

    building_ticker: str = Field(alias="BuildingTicker")
    recipe_name: str = Field(alias="RecipeName")
    inputs: list[FIORecipeIO] = Field(default_factory=list, alias="Inputs")
    outputs: list[FIORecipeIO] = Field(default_factory=list, alias="Outputs")
    time_ms: int = Field(alias="TimeMs")

    model_config = {"populate_by_name": True, "extra": "ignore"}


class FIOBuildingRecipeIO(BaseModel):
    """Input or output of a building recipe (uses CommodityTicker)."""

    commodity_ticker: str = Field(alias="CommodityTicker")
    amount: int = Field(alias="Amount")

    model_config = {"populate_by_name": True, "extra": "ignore"}


class FIOBuildingRecipe(BaseModel):
    """Recipe embedded in building data."""

    building_recipe_id: str = Field(alias="BuildingRecipeId", default="")
    recipe_name: str = Field(alias="RecipeName", default="")
    standard_recipe_name: str = Field(alias="StandardRecipeName", default="")
    duration_ms: int = Field(alias="DurationMs", default=0)
    inputs: list[FIOBuildingRecipeIO] = Field(default_factory=list, alias="Inputs")
    outputs: list[FIOBuildingRecipeIO] = Field(default_factory=list, alias="Outputs")

    model_config = {"populate_by_name": True, "extra": "ignore"}


class FIOBuildingFull(BaseModel):
    """Full building data including workforce counts and recipes.

    Used for COGM calculations and building info display.
    """

    building_id: str = Field(alias="BuildingId", default="")
    ticker: str = Field(alias="Ticker")
    name: PrettifiedName = Field(alias="Name")
    expertise: str | None = Field(alias="Expertise", default=None)
    area_cost: int = Field(alias="AreaCost")
    pioneers: int = Field(alias="Pioneers", default=0)
    settlers: int = Field(alias="Settlers", default=0)
    technicians: int = Field(alias="Technicians", default=0)
    engineers: int = Field(alias="Engineers", default=0)
    scientists: int = Field(alias="Scientists", default=0)
    building_costs: list[FIOBuildingCost] = Field(
        default_factory=list, alias="BuildingCosts"
    )
    recipes: list[FIOBuildingRecipe] = Field(default_factory=list, alias="Recipes")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    def get_workforce_count(self, workforce_type: str) -> int:
        """Get workforce count by type name (e.g., 'Pioneers', 'PIONEER')."""
        normalized = workforce_type.lower().rstrip("s")
        mapping = {
            "pioneer": self.pioneers,
            "settler": self.settlers,
            "technician": self.technicians,
            "engineer": self.engineers,
            "scientist": self.scientists,
        }
        return mapping.get(normalized, 0)


class FIOExchangeOrder(BaseModel):
    """A single buy or sell order on an exchange."""

    company_code: str = Field(alias="CompanyCode")
    item_count: int | None = Field(alias="ItemCount", default=None)
    item_cost: float | None = Field(alias="ItemCost", default=None)

    model_config = {"populate_by_name": True, "extra": "ignore"}


class FIOExchangeData(BaseModel):
    """Exchange price data from the FIO API."""

    material_ticker: str = Field(alias="MaterialTicker")
    exchange_code: str = Field(alias="ExchangeCode")
    mm_buy: float | None = Field(alias="MMBuy", default=None)
    mm_sell: float | None = Field(alias="MMSell", default=None)
    price: float | None = Field(alias="Price", default=None)
    price_time_epoch_ms: int | None = Field(alias="PriceTimeEpochMs", default=None)
    high: float | None = Field(alias="High", default=None)
    all_time_high: float | None = Field(alias="AllTimeHigh", default=None)
    low: float | None = Field(alias="Low", default=None)
    all_time_low: float | None = Field(alias="AllTimeLow", default=None)
    ask: float | None = Field(alias="Ask", default=None)
    ask_count: int | None = Field(alias="AskCount", default=None)
    bid: float | None = Field(alias="Bid", default=None)
    bid_count: int | None = Field(alias="BidCount", default=None)
    supply: int | None = Field(alias="Supply", default=None)
    demand: int | None = Field(alias="Demand", default=None)
    traded: int | None = Field(alias="Traded", default=None)
    volume_amount: float | None = Field(alias="VolumeAmount", default=None)
    price_average: float | None = Field(alias="PriceAverage", default=None)
    narrow_price_band_low: float | None = Field(
        alias="NarrowPriceBandLow", default=None
    )
    narrow_price_band_high: float | None = Field(
        alias="NarrowPriceBandHigh", default=None
    )
    wide_price_band_low: float | None = Field(alias="WidePriceBandLow", default=None)
    wide_price_band_high: float | None = Field(alias="WidePriceBandHigh", default=None)
    buying_orders: list[FIOExchangeOrder] = Field(
        default_factory=list, alias="BuyingOrders"
    )
    selling_orders: list[FIOExchangeOrder] = Field(
        default_factory=list, alias="SellingOrders"
    )

    model_config = {"populate_by_name": True, "extra": "ignore"}


class FIOPlanetResource(BaseModel):
    """Resource on a planet."""

    material_id: str = Field(alias="MaterialId")
    resource_type: str = Field(alias="ResourceType", default="")
    factor: float = Field(alias="Factor", default=0.0)

    model_config = {"populate_by_name": True, "extra": "ignore"}


class FIOPlanetFull(BaseModel):
    """Full planet data from the FIO API."""

    planet_id: str = Field(alias="PlanetId", default="")
    planet_name: str = Field(alias="PlanetName")
    planet_natural_id: str = Field(alias="PlanetNaturalId")
    surface: bool = Field(alias="Surface", default=True)
    pressure: float = Field(alias="Pressure", default=1.0)
    gravity: float = Field(alias="Gravity", default=1.0)
    temperature: float = Field(alias="Temperature", default=20.0)
    fertility: float | None = Field(alias="Fertility", default=None)
    resources: list[FIOPlanetResource] = Field(default_factory=list, alias="Resources")

    model_config = {"populate_by_name": True, "extra": "ignore"}
