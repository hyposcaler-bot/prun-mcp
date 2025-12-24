"""FastMCP server for Prosperous Universe."""

import logging
import sys

# Configure logging to stderr (required for STDIO transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

# Import mcp instance and tools to register them
from prun_mcp.app import mcp  # noqa: E402
from prun_mcp.tools import materials  # noqa: F401, E402


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
