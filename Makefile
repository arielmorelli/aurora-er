.DEFAULT_GOAL := help
.PHONY: help install run test check

help: ## Show available targets
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-10s %s\n", $$1, $$2}'

install: ## Create the environment and install git hooks
	uv sync
	uv run pre-commit install

run: ## Run the battery dispatch model
	uv run python -m aurora_er

test: ## Run the unit tests
	uv run pytest

check: ## Run every quality gate (lint, format, types, tests) on all files
	uv run pre-commit run --all-files
