"""Building cost calculation tool."""

import logging

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError
from prun_mcp.prun_lib.building import (
    BuildingCostError,
    calculate_building_cost_async,
)
from prun_mcp.prun_lib.exchange import InvalidExchangeError

logger = logging.getLogger(__name__)


@mcp.tool()
async def calculate_building_cost(
    building_ticker: str,
    planet: str,
    exchange: str | None = None,
) -> str | list[TextContent]:
    """Calculate total cost to build a building on a planet.

    Calculates the complete material requirements including base building
    costs and infrastructure materials based on planetary environment
    (surface type, pressure, gravity, temperature).

    Args:
        building_ticker: Building ticker (e.g., "FP", "HB1", "FRM").
        planet: Planet identifier (name, natural ID, or planet ID).
        exchange: Optional exchange code for cost calculation (e.g., "CI1").
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.

    Returns:
        TOON-encoded breakdown of materials including base costs
        and infrastructure requirements based on planet environment.
        If exchange is provided, includes price and cost per material.
    """
    try:
        result = await calculate_building_cost_async(
            building_ticker=building_ticker,
            planet=planet,
            exchange=exchange,
        )

        return toon_encode(result.model_dump(by_alias=True))

    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]
    except BuildingCostError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
