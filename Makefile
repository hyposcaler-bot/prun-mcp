.PHONY: test lint typecheck check run docker-build docker-run clean

# Run tests
test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD="" uv run --frozen pytest

# Lint and format code
lint:
	uv run --frozen ruff check .
	uv run --frozen ruff format .

# Type checking
typecheck:
	uv run --frozen pyright

# Run all checks (lint, typecheck, test)
check: lint typecheck test

# Run MCP server locally
run:
	uv run prun-mcp

# Build Docker image
docker-build:
	docker build -t prun-mcp .

# Run in Docker (STDIO mode)
docker-run: docker-build
	docker run -i prun-mcp

# Clean build artifacts
clean:
	rm -rf .pytest_cache __pycache__ .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
