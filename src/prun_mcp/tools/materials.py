"""Material-related MCP tools."""

import json
import logging

from mcp.types import TextContent

from prun_mcp.app import mcp
from prun_mcp.fio import FIOApiError, FIOClient, FIONotFoundError

# TODO: Switch to TOON encoding when toon_format encoder is implemented
# from toon_format import encode as toon_encode

logger = logging.getLogger(__name__)

# Shared FIO client instance
_fio_client: FIOClient | None = None


def get_fio_client() -> FIOClient:
    """Get or create the shared FIO client."""
    global _fio_client
    if _fio_client is None:
        _fio_client = FIOClient()
    return _fio_client


@mcp.tool()
async def get_material_info(ticker: str) -> str | list[TextContent]:
    """Get information about a material by its ticker symbol.

    Args:
        ticker: Material ticker symbol (e.g., "BSE", "RAT", "H2O")

    Returns:
        TOON-encoded material data including name, category, weight, and volume.
    """
    client = get_fio_client()

    try:
        data = await client.get_material(ticker.upper())
        # TODO: Use toon_encode(data) when encoder is implemented
        return json.dumps(data, indent=2)

    except FIONotFoundError:
        return [TextContent(type="text", text=f"Material '{ticker}' not found")]

    except FIOApiError as e:
        logger.exception("FIO API error while fetching material")
        return [TextContent(type="text", text=f"FIO API error: {e}")]
