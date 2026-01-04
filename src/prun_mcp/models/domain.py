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


class COGMInputBreakdown(BaseModel):
    """A single input material in COGM breakdown."""

    ticker: str = Field(serialization_alias="Ticker")
    daily_amount: float = Field(serialization_alias="DailyAmount")
    price: float | None = Field(default=None, serialization_alias="Price")
    daily_cost: float | None = Field(default=None, serialization_alias="DailyCost")


class COGMConsumableBreakdown(BaseModel):
    """A single consumable in COGM breakdown."""

    ticker: str = Field(serialization_alias="Ticker")
    workforce_type: str = Field(serialization_alias="WorkforceType")
    daily_amount: float = Field(serialization_alias="DailyAmount")
    price: float | str | None = Field(default=None, serialization_alias="Price")
    daily_cost: float | None = Field(default=None, serialization_alias="DailyCost")
    self_consumed: bool = Field(default=False, serialization_alias="SelfConsumed")


class COGMOutput(BaseModel):
    """COGM output information."""

    ticker: str = Field(serialization_alias="Ticker")
    daily_output: float = Field(serialization_alias="DailyOutput")


class COGMTotals(BaseModel):
    """COGM cost totals."""

    daily_input_cost: float
    daily_consumable_cost: float
    daily_total_cost: float


class COGMBreakdown(BaseModel):
    """COGM cost breakdown."""

    inputs: list[COGMInputBreakdown]
    consumables: list[COGMConsumableBreakdown]


class COGMSelfConsumption(BaseModel):
    """Self-consumption information for COGM."""

    consumed: dict[str, float]
    net_output: float


class COGMResult(BaseModel):
    """Complete COGM calculation result."""

    recipe: str
    building: str
    efficiency: float
    exchange: str
    self_consume: bool
    output: COGMOutput
    cogm_per_unit: float
    breakdown: COGMBreakdown
    totals: COGMTotals
    self_consumption: COGMSelfConsumption | None = None
    missing_prices: list[str] = Field(default_factory=list)
