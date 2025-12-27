"""Building efficiency documentation resources."""

from prun_mcp.app import mcp

EFFICIENCY_OVERVIEW = """
# Building Efficiency

Efficiency determines production speed. Formula:

  Efficiency = Base x (1 + Expert%) x (1 + CoGC%)

Where Base = Workforce Satisfaction x Building Condition (typically 100%)

## Factors

1. Workforce Satisfaction - Workers need consumables (RAT, DW, OVE, etc.)
2. Building Condition - Degrades over time, requires maintenance materials
3. Experts - Company experts boost specific industries (up to ~28.4%)
4. CoGC Programs - Planet programs boost industries (up to 25%)

## Example
- 3 Food experts: +12%
- Maxed ADVERTISING_FOOD_INDUSTRIES: +25%
- Efficiency = 100% x 1.12 x 1.25 = 140%

See sub-resources for details on each factor.
"""

WORKFORCE_INFO = """
# Workforce Satisfaction

Workers consume materials daily. Satisfaction = 100% when needs are met.

## Consumption Rate
- Amount per 100 workers per day (from FIO workforce API)
- Essential needs (RAT, DW) have higher priority
- Luxury items (COF, PWO) boost satisfaction above 100%

## Impact
- 0% satisfaction = 0% base efficiency
- 100% satisfaction = 100% base efficiency
- Above 100% possible with luxury consumables

Use get_workforce_needs tool for exact consumption rates.
"""

EXPERTS_INFO = """
# Expert Bonuses

Company experts boost production in their specialty.

## Expert Types
Match building expertise: AGRICULTURE, CHEMISTRY, CONSTRUCTION,
ELECTRONICS, FOOD_INDUSTRIES, FUEL_REFINING, MANUFACTURING,
METALLURGY, RESOURCE_EXTRACTION

## Bonus Calculation
Diminishing returns per expert:
- 1 expert: ~6%
- 2 experts: ~10%
- 3 experts: ~12%
- 4 experts: ~20%
- 5 experts: ~28.4% (maximum)

## Formula
Experts multiply with other bonuses:
  Final = Base x (1 + Expert%) x (1 + CoGC%)
"""

COGC_INFO = """
# Chamber of Global Commerce (CoGC) Programs

Planet-wide programs that boost specific industries.

## ADVERTISING Programs
Boost production efficiency for a specific industry:
- ADVERTISING_AGRICULTURE
- ADVERTISING_CHEMISTRY
- ADVERTISING_CONSTRUCTION
- ADVERTISING_ELECTRONICS
- ADVERTISING_FOOD_INDUSTRIES
- ADVERTISING_FUEL_REFINING
- ADVERTISING_MANUFACTURING
- ADVERTISING_METALLURGY
- ADVERTISING_RESOURCE_EXTRACTION

## Bonus
- Maximum: 25% efficiency bonus
- Scales with program funding level
- Only applies to buildings matching the advertised industry

## Checking Active Programs
Use get_planet_info tool - COGCPrograms field shows active programs.
"""

CONDITION_INFO = """
# Building Condition

Buildings degrade over time and from environmental factors.

## Degradation Sources
- Time: Natural wear
- Environment: Hostile atmospheres, pressure, gravity, temperature

## Maintenance
- Requires building materials (MCG, etc.)
- Higher tier buildings need more maintenance
- Neglected buildings produce at reduced efficiency

## Impact
- 100% condition = full base efficiency
- Degraded condition = proportionally reduced output
- 0% condition = building non-functional
"""


@mcp.resource("buildings://efficiency")
def get_efficiency_overview() -> str:
    """Overview of building efficiency mechanics and formula."""
    return EFFICIENCY_OVERVIEW.strip()


@mcp.resource("buildings://efficiency/workforce")
def get_efficiency_workforce() -> str:
    """Workforce satisfaction impact on building efficiency."""
    return WORKFORCE_INFO.strip()


@mcp.resource("buildings://efficiency/experts")
def get_efficiency_experts() -> str:
    """Expert bonus system for building efficiency."""
    return EXPERTS_INFO.strip()


@mcp.resource("buildings://efficiency/cogc")
def get_efficiency_cogc() -> str:
    """CoGC program bonuses for building efficiency."""
    return COGC_INFO.strip()


@mcp.resource("buildings://efficiency/condition")
def get_efficiency_condition() -> str:
    """Building condition impact on efficiency."""
    return CONDITION_INFO.strip()
