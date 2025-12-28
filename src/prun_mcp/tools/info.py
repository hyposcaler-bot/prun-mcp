"""Server info tools."""

import os
import subprocess
import time
from typing import Any

from importlib.metadata import version as pkg_version

from toon_format import encode as toon_encode

from prun_mcp.app import mcp


def _get_git_info() -> dict[str, str | None]:
    """Get git branch and commit info if available.

    Returns:
        Dict with 'branch' and 'commit' keys (None if not available).
    """
    result: dict[str, str | None] = {"branch": None, "commit": None}

    try:
        # Check if we're in a git repo
        result["branch"] = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()

        result["commit"] = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        pass

    return result


@mcp.tool()
def get_version() -> str:
    """Get prun-mcp server version.

    Returns:
        Server version string.
    """
    # Get package version (from setuptools-scm at build time)
    version = pkg_version("prun-mcp")

    # Check if this looks like a release version (no .dev or +)
    is_release = ".dev" not in version and "+" not in version

    if is_release:
        return version

    # For dev builds, try to get more detailed info
    # First check environment variables (set in Docker builds)
    branch = os.environ.get("PRUN_MCP_GIT_BRANCH")
    commit = os.environ.get("PRUN_MCP_GIT_COMMIT")

    # Fall back to git commands if env vars not present
    if not branch or not commit:
        git_info = _get_git_info()
        branch = branch or git_info["branch"]
        commit = commit or git_info["commit"]

    # Format version string
    if branch and commit:
        return f"{branch}@{commit}"
    elif commit:
        return f"dev@{commit}"
    else:
        # Fall back to package version
        return version


@mcp.tool()
def get_cache_info() -> str:
    """Get cache status for all data caches.

    Returns:
        TOON-encoded cache info including validity, counts, age, and file paths.
    """
    # Import cache getters here to avoid circular imports
    from prun_mcp.tools.buildings import get_buildings_cache
    from prun_mcp.tools.materials import get_materials_cache
    from prun_mcp.tools.permit_io import get_workforce_cache
    from prun_mcp.tools.recipes import get_recipes_cache

    caches_info: list[dict[str, Any]] = []
    now = time.time()

    # Materials cache
    materials_cache = get_materials_cache()
    caches_info.append(_get_cache_status("materials", materials_cache, now))

    # Buildings cache
    buildings_cache = get_buildings_cache()
    caches_info.append(_get_cache_status("buildings", buildings_cache, now))

    # Recipes cache
    recipes_cache = get_recipes_cache()
    caches_info.append(_get_cache_status("recipes", recipes_cache, now))

    # Workforce cache
    workforce_cache = get_workforce_cache()
    caches_info.append(_get_cache_status("workforce", workforce_cache, now))

    return toon_encode({"caches": caches_info})


def _get_cache_status(name: str, cache: Any, now: float) -> dict[str, Any]:
    """Get status info for a single cache.

    Args:
        name: Cache name for display.
        cache: Cache instance with is_valid(), cache_file, ttl_hours.
        now: Current timestamp for age calculation.

    Returns:
        Dict with cache status info.
    """
    cache_file = cache.cache_file
    valid = cache.is_valid()

    # Get count based on cache type
    if hasattr(cache, "material_count"):
        count = cache.material_count()
    elif hasattr(cache, "building_count"):
        count = cache.building_count()
    elif hasattr(cache, "recipe_count"):
        count = cache.recipe_count()
    else:
        # Workforce cache doesn't have a count method, check data directly
        count = len(cache.get_all_needs()) if hasattr(cache, "get_all_needs") else 0

    # Calculate age if file exists
    age_hours: float | None = None
    if cache_file.exists():
        mtime = cache_file.stat().st_mtime
        age_hours = round((now - mtime) / 3600, 2)

    return {
        "name": name,
        "valid": valid,
        "count": count,
        "path": str(cache_file.resolve()),
        "age_hours": age_hours,
        "ttl_hours": cache.ttl_hours,
    }
