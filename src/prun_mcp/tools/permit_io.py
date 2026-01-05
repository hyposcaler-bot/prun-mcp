"""Permit daily I/O calculator tool."""

import logging
from typing import Any

from mcp.types import TextContent
from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError
from prun_mcp.prun_lib.base_io import BaseIOValidationError, calculate_base_io
from prun_mcp.prun_lib.exchange import InvalidExchangeError

logger = logging.getLogger(__name__)


@mcp.tool()
async def calculate_permit_io(
    production: list[dict[str, Any]],
    habitation: list[dict[str, Any]],
    exchange: str,
    permits: int = 1,
    extraction: list[dict[str, Any]] | None = None,
    planet: str | None = None,
) -> str | list[TextContent]:
    """Calculate daily material I/O for a base.

    Args:
        production: List of production lines with recipe, count, efficiency.
        habitation: List of habitation buildings with building, count.
        exchange: Exchange code for pricing. Valid: AI1, CI1, CI2, IC1, NC1, NC2.
        permits: Number of permits for this base (default: 1).
        extraction: Optional extraction operations with building, resource, count.
        planet: Planet identifier (required if extraction is provided).

    Returns:
        TOON-encoded daily I/O breakdown with materials, workforce, area.
    """
    try:
        result = await calculate_base_io(
            production=production,
            habitation=habitation,
            exchange=exchange,
            permits=permits,
            extraction=extraction,
            planet=planet,
        )

        return toon_encode(result)

    except InvalidExchangeError as e:
        return [TextContent(type="text", text=str(e))]
    except BaseIOValidationError as e:
        return [TextContent(type="text", text=str(e))]
    except FIOApiError as e:
        logger.exception("FIO API error while calculating base I/O")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
