FROM python:3.12-slim

WORKDIR /app

# Build args for version info
ARG GIT_BRANCH=unknown
ARG GIT_COMMIT=unknown

# Set version info as environment variables (used by get_version at runtime)
ENV PRUN_MCP_GIT_BRANCH=${GIT_BRANCH}
ENV PRUN_MCP_GIT_COMMIT=${GIT_COMMIT}

# Install git (required for git+https dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Install dependencies
RUN uv sync --frozen --no-dev

# Run the MCP server (STDIO mode)
CMD ["uv", "run", "--no-sync", "prun-mcp"]
