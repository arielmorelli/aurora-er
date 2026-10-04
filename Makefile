.DEFAULT_GOAL := help
.PHONY: help install run run-example test check ui-clean

help: ## Show available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Create the environment and install git hooks
	uv sync
	uv run pre-commit install

run-example: ## Run the model on the provided data in inputs/
	uv run python -m aurora_er.example inputs

run: ## Start the Streamlit UI; runs are stored in sessions/
	AURORA_SESSIONS_DIR=sessions AURORA_INPUTS_DIR=inputs uv run streamlit run src/aurora_er/ui/app.py

test: ## Run the unit tests
	uv run pytest

check: ## Run every quality gate (lint, format, types, tests) on all files
	uv run pre-commit run --all-files

ui-clean: ## Delete generated files: UI sessions, caches and build output (keeps .venv)
	rm -rf sessions .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov dist build
	find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} +
