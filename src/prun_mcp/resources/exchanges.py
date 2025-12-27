"""Exchange data and MCP resource."""

from prun_mcp.app import mcp

# Exchange code to name mapping - canonical source of exchange data
EXCHANGES: dict[str, str] = {
    "AI1": "Antares Station",
    "CI1": "Benten Station",
    "CI2": "Arclight Exchange",
    "IC1": "Hortus Station",
    "NC1": "Moria Station",
    "NC2": "Hubur Exchange",
}

VALID_EXCHANGES = set(EXCHANGES.keys())


def format_exchange_list() -> str:
    """Format exchange list for display.

    Returns:
        Human-readable table of exchanges.
    """
    lines = ["Code  Name"]
    lines.append("-" * 25)
    for code, name in EXCHANGES.items():
        lines.append(f"{code}   {name}")
    return "\n".join(lines)


@mcp.resource("exchange://list")
def list_exchanges() -> str:
    """List all commodity exchanges with codes and names.

    Returns:
        Human-readable table of exchanges showing code and name.
        Use codes (e.g., CI1) in exchange tools.
    """
    return format_exchange_list()
