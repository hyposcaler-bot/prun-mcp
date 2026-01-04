"""Domain models for prun-mcp business logic.

These models represent the structured outputs of business logic operations.
They are independent of both the FIO API format and MCP presentation format.
"""

from pydantic import BaseModel, Field


class MaterialCost(BaseModel):
    """A single material requirement with optional pricing."""

    ticker: str
    amount: int
    price: float | None = None
    cost: float | None = None


class EnvironmentInfo(BaseModel):
    """Planet environment classification.

    Describes the environmental conditions that affect infrastructure costs.
    """

    surface_type: str = Field(description="'rocky' or 'gaseous'")
    conditions: list[str] = Field(
        default_factory=list,
        description="Environmental conditions: low-pressure, high-pressure, "
        "low-gravity, high-gravity, cold, hot",
    )

    @property
    def description(self) -> str:
        """Format environment as comma-separated string."""
        parts = [self.surface_type] + self.conditions
        return ", ".join(parts)


class BuildingCostResult(BaseModel):
    """Complete building cost calculation result.

    Contains all materials needed to construct a building on a specific planet,
    including base building materials and infrastructure requirements.
    """

    building_ticker: str
    building_name: str
    planet_name: str
    planet_id: str
    area: int
    materials: list[MaterialCost]
    environment: EnvironmentInfo
    exchange: str | None = None
    total_cost: float | None = None
    missing_prices: list[str] = Field(default_factory=list)

    def to_output_dict(self) -> dict:
        """Convert to dictionary format suitable for TOON encoding.

        This produces the same output structure as the original tool
        for backwards compatibility.
        """
        result: dict = {
            "building": self.building_ticker,
            "planet": f"{self.planet_name} ({self.planet_id})",
            "area": self.area,
        }

        if self.exchange:
            result["exchange"] = self.exchange

        materials_list = []
        for mat in self.materials:
            entry: dict = {
                "material": mat.ticker,
                "amount": mat.amount,
            }
            if self.exchange:
                entry["price"] = mat.price
                entry["cost"] = mat.cost
            materials_list.append(entry)

        result["materials"] = materials_list

        if self.exchange:
            result["total_cost"] = self.total_cost
            if self.missing_prices:
                result["missing_prices"] = self.missing_prices

        result["environment"] = self.environment.description

        return result
