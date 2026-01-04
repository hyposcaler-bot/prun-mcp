"""Pydantic models for FIO API responses.

These models represent the data returned by the FIO REST API.
They use aliases to map from the API's PascalCase to Python's snake_case.
"""

from pydantic import BaseModel, Field


class FIOBuildingCost(BaseModel):
    """A single material cost entry for a building."""

    commodity_ticker: str = Field(alias="CommodityTicker")
    amount: int = Field(alias="Amount")

    model_config = {"populate_by_name": True}


class FIOBuilding(BaseModel):
    """Building data from the FIO API.

    Contains core building information needed for cost calculations.
    Additional fields from the API are ignored.
    """

    ticker: str = Field(alias="Ticker")
    name: str = Field(alias="Name")
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
