"""Domain models for prun-mcp business logic.

These models represent the structured outputs of business logic operations.
They are independent of both the FIO API format and MCP presentation format.
"""

from pydantic import BaseModel, Field, field_serializer


class MaterialCost(BaseModel):
    """A single material requirement with optional pricing."""

    ticker: str = Field(serialization_alias="material")
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

    building_ticker: str = Field(serialization_alias="building")
    building_name: str
    planet_name: str
    planet_id: str
    area: int
    materials: list[MaterialCost]
    environment: EnvironmentInfo
    exchange: str | None = None
    total_cost: float | None = None
    missing_prices: list[str] = Field(default_factory=list)

    @field_serializer("environment")
    def serialize_environment(self, env: EnvironmentInfo) -> str:
        """Serialize environment as description string."""
        return env.description
