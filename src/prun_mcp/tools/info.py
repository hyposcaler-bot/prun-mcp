"""Server info tools."""

from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.prun_lib.info import get_cache_info_data, get_version_info


@mcp.tool()
def get_version() -> str:
    """Get prun-mcp server version.

    Returns:
        Server version string.
    """
    return get_version_info()


@mcp.tool()
def get_cache_info() -> str:
    """Get cache status for all data caches.

    Returns:
        TOON-encoded cache info including validity, counts, age, and file paths.
    """
    return toon_encode(get_cache_info_data())
