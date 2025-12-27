"""Community-derived game mechanics resources."""

from pathlib import Path

from prun_mcp.app import mcp

# Path to community mechanics content
MECHANICS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "data"
    / "community-mechanics"
    / "content"
)

# Topics to expose (skip fio and stl-flight - not useful mechanics)
TOPICS = [
    "arc",
    "building-degradation",
    "hq",
    "planet",
    "population-infrastructure",
    "ship-blueprints",
    "workforce",
]


def _read_topic(topic: str) -> str:
    """Read markdown content for a topic.

    Args:
        topic: The topic folder name.

    Returns:
        The markdown content, or an error message if not found.
    """
    path = MECHANICS_DIR / topic / "_index.md"
    if not path.exists():
        return f"Content not found for topic: {topic}"
    return path.read_text()


def format_topics_list() -> str:
    """Format the list of available topics.

    Returns:
        Human-readable list of available mechanics topics.
    """
    lines = ["Available community-derived game mechanics:"]
    lines.append("")
    for topic in TOPICS:
        lines.append(f"  pct-mechanics://{topic}")
    return "\n".join(lines)


@mcp.resource("pct-mechanics://list")
def list_mechanics() -> str:
    """List available game mechanics documentation topics.

    Returns:
        List of available pct-mechanics:// resource URIs.
    """
    return format_topics_list()


@mcp.resource("pct-mechanics://arc")
def arc_mechanics() -> str:
    """ARC (Adversity Response Challenge) level formula.

    Returns:
        Markdown documentation of ARC mechanics.
    """
    return _read_topic("arc")


@mcp.resource("pct-mechanics://building-degradation")
def building_degradation_mechanics() -> str:
    """Building condition and repair cost formulas.

    Returns:
        Markdown documentation of building degradation mechanics.
    """
    return _read_topic("building-degradation")


@mcp.resource("pct-mechanics://hq")
def hq_mechanics() -> str:
    """HQ upgrade costs and efficiency multiplier formulas.

    Returns:
        Markdown documentation of HQ mechanics.
    """
    return _read_topic("hq")


@mcp.resource("pct-mechanics://planet")
def planet_mechanics() -> str:
    """Planet resource extraction formulas.

    Returns:
        Markdown documentation of planet extraction mechanics.
    """
    return _read_topic("planet")


@mcp.resource("pct-mechanics://population-infrastructure")
def population_infrastructure_mechanics() -> str:
    """Population needs, happiness, and growth formulas.

    Returns:
        Markdown documentation of population infrastructure mechanics.
    """
    return _read_topic("population-infrastructure")


@mcp.resource("pct-mechanics://ship-blueprints")
def ship_blueprints_mechanics() -> str:
    """Ship construction formulas and component volumes.

    Returns:
        Markdown documentation of ship blueprint mechanics.
    """
    return _read_topic("ship-blueprints")


@mcp.resource("pct-mechanics://workforce")
def workforce_mechanics() -> str:
    """Workforce efficiency formulas for all worker types.

    Returns:
        Markdown documentation of workforce mechanics.
    """
    return _read_topic("workforce")
