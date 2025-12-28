.PHONY: help test lint typecheck check run docker-build docker-run clean

.DEFAULT_GOAL := help

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

test: ## Run tests
	PYTEST_DISABLE_PLUGIN_AUTOLOAD="" uv run --frozen pytest

lint: ## Lint and format code
	uv run --frozen ruff check .
	uv run --frozen ruff format .

typecheck: ## Run type checking
	uv run --frozen pyright

check: lint typecheck test ## Run all checks (lint, typecheck, test)

run: ## Run MCP server locally
	uv run prun-mcp

docker-build: ## Build Docker image
	docker build \
		--build-arg GIT_BRANCH=$$(git rev-parse --abbrev-ref HEAD) \
		--build-arg GIT_COMMIT=$$(git rev-parse --short HEAD) \
		-t prun-mcp:latest .

docker-run: docker-build ## Run in Docker (STDIO mode)
	docker run -i prun-mcp:latest

clean: ## Clean build artifacts
	rm -rf .pytest_cache __pycache__ .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
