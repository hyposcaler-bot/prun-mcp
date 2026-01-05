"""COGM (Cost of Goods Manufactured) calculation tool."""

import logging

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError
from prun_mcp.prun_lib.cogm import (
    COGMCalculationError,
    calculate_cogm as calculate_cogm_logic,
)
from prun_mcp.prun_lib.exchange import InvalidExchangeError

logger = logging.getLogger(__name__)


@mcp.tool()
async def calculate_cogm(
    recipe: str,
    exchange: str,
    efficiency: float = 1.0,
    self_consume: bool = False,
) -> str | list[TextContent]:
    """Calculate Cost of Goods Manufactured for a recipe.

    Args:
        recipe: Recipe name (e.g., "1xGRN 1xBEA 1xNUT=>10xRAT")
        exchange: Exchange code for pricing (e.g., "CI1").
                  Valid: AI1, CI1, CI2, IC1, NC1, NC2.
        efficiency: Production efficiency multiplier (default: 1.0 = 100%)
        self_consume: If True, use produced output to satisfy workforce needs.

    Returns:
        TOON-encoded COGM breakdown including cogm_per_unit, costs, and output.
    """
    try:
        result = await calculate_cogm_logic(
            recipe_name=recipe,
            exchange=exchange,
            efficiency=efficiency,
            self_consume=self_consume,
        )

        # Convert to dict for TOON encoding
        result_dict = result.model_dump(by_alias=True, exclude_none=True)

        # Rename keys to match expected output format
        if "self_consumption" in result_dict and result.self_consumption is not None:
            result_dict["self_consumption"] = result.self_consumption.model_dump()

        return toon_encode(result_dict)

    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]
    except COGMCalculationError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while calculating COGM")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
