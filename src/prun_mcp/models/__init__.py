"""Pydantic models for prun-mcp."""

from prun_mcp.models.domain import (
    BuildingCostResult,
    COGMBreakdown,
    COGMConsumableBreakdown,
    COGMInputBreakdown,
    COGMOutput,
    COGMResult,
    COGMSelfConsumption,
    COGMTotals,
    EnvironmentInfo,
    MaterialCost,
)
from prun_mcp.models.fio import (
    FIOBuilding,
    FIOBuildingCost,
    FIOBuildingFull,
    FIOBuildingRecipe,
    FIOBuildingRecipeIO,
    FIOExchangeData,
    FIOExchangeOrder,
    FIOMaterial,
    FIOPlanet,
    FIOPlanetFull,
    FIOPlanetResource,
    FIORecipe,
    FIORecipeIO,
)

__all__ = [
    # FIO models
    "FIOBuilding",
    "FIOBuildingCost",
    "FIOBuildingFull",
    "FIOBuildingRecipe",
    "FIOBuildingRecipeIO",
    "FIOExchangeData",
    "FIOExchangeOrder",
    "FIOMaterial",
    "FIOPlanet",
    "FIOPlanetFull",
    "FIOPlanetResource",
    "FIORecipe",
    "FIORecipeIO",
    # Domain models
    "BuildingCostResult",
    "COGMBreakdown",
    "COGMConsumableBreakdown",
    "COGMInputBreakdown",
    "COGMOutput",
    "COGMResult",
    "COGMSelfConsumption",
    "COGMTotals",
    "EnvironmentInfo",
    "MaterialCost",
]
