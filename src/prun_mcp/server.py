"""FastMCP server for Prosperous Universe."""

import logging
import sys
from typing import Literal

import anyio

# Configure logging to stderr (required for STDIO transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

# Import mcp instance and tools to register them
from prun_mcp.app import mcp  # noqa: E402
from prun_mcp.fio import get_fio_client  # noqa: E402
from prun_mcp.tools import buildings  # noqa: F401, E402
from prun_mcp.tools import cogm  # noqa: F401, E402
from prun_mcp.tools import exchange  # noqa: F401, E402
from prun_mcp.tools import materials  # noqa: F401, E402
from prun_mcp.tools import planets  # noqa: F401, E402
from prun_mcp.tools import recipes  # noqa: F401, E402

logger = logging.getLogger(__name__)


async def _shutdown() -> None:
    """Close shared clients during server shutdown."""
    await get_fio_client().close()


async def _run_server(
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
    mount_path: str | None = None,
) -> None:
    """Run the MCP server and close shared resources on shutdown."""
    try:
        match transport:
            case "stdio":
                await mcp.run_stdio_async()
            case "sse":  # pragma: no cover
                await mcp.run_sse_async(mount_path)
            case "streamable-http":  # pragma: no cover
                await mcp.run_streamable_http_async()
            case _:
                raise ValueError(f"Unknown transport: {transport}")
    finally:
        try:
            await _shutdown()
        except Exception:
            logger.debug(
                "Failed to close the FIO client during shutdown", exc_info=True
            )


def main() -> None:
    """Run the MCP server."""
    anyio.run(_run_server)


if __name__ == "__main__":
    main()
