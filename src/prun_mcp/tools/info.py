"""Server info tools."""

import os
import subprocess

from importlib.metadata import version as pkg_version

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
