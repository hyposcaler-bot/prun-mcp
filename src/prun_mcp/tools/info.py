"""Server info tools."""

import os
import subprocess
import time
from typing import Any

from importlib.metadata import version as pkg_version

from toon_format import encode as toon_encode

from prun_mcp.app import mcp
from prun_mcp.cache import (
    get_buildings_cache,
    get_materials_cache,
    get_recipes_cache,
    get_workforce_cache,
)


def _get_git_info() -> dict[str, str | None]:
    """Get git branch and commit info if available."""
    result: dict[str, str | None] = {"branch": None, "commit": None}

    try:
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
    branch = os.environ.get("PRUN_MCP_GIT_BRANCH")
    commit = os.environ.get("PRUN_MCP_GIT_COMMIT")

    if not branch or not commit or branch == "unknown":
        git_info = _get_git_info()
        branch = git_info["branch"] or branch
        commit = git_info["commit"] or commit

    if branch and commit and branch != "unknown":
        short_commit = commit[:7] if len(commit) > 7 else commit
        return f"{branch}@{short_commit}"

    return pkg_version("prun-mcp")


@mcp.tool()
def get_cache_info() -> str:
    """Get cache status for all data caches.

    Returns:
        TOON-encoded cache info including validity, counts, age, and file paths.
    """
    caches_info: list[dict[str, Any]] = []
    now = time.time()

    materials_cache = get_materials_cache()
    caches_info.append(_get_cache_status("materials", materials_cache, now))

    buildings_cache = get_buildings_cache()
    caches_info.append(_get_cache_status("buildings", buildings_cache, now))

    recipes_cache = get_recipes_cache()
    caches_info.append(_get_cache_status("recipes", recipes_cache, now))

    workforce_cache = get_workforce_cache()
    caches_info.append(_get_cache_status("workforce", workforce_cache, now))

    return toon_encode({"caches": caches_info})


def _get_cache_status(name: str, cache: Any, now: float) -> dict[str, Any]:
    """Get status info for a single cache."""
    cache_file = cache.cache_file
    valid = cache.is_valid()

    if hasattr(cache, "material_count"):
        count = cache.material_count()
    elif hasattr(cache, "building_count"):
        count = cache.building_count()
    elif hasattr(cache, "recipe_count"):
        count = cache.recipe_count()
    else:
        count = len(cache.get_all_needs()) if hasattr(cache, "get_all_needs") else 0

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
