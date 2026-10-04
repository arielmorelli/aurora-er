# 0002. Python tooling: uv, ruff, mypy, pytest, pre-commit

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

The project needs reproducible environments, consistent style, type safety and automated tests, with as little setup friction as possible for reviewers who clone the repository. These tools were set as a requirement for the project, so they are recorded together in a single decision.

## Decision

| Concern | Tool | Notes |
| --- | --- | --- |
| Environment, dependencies, build | **uv** | `uv.lock` is committed; `uv_build` is the build backend |
| Linting and formatting | **ruff** | Replaces flake8, isort, black, pyupgrade |
| Static type checking | **mypy** | `strict = true` over `src/` and `tests/` |
| Testing | **pytest** | Unit tests under `tests/` |
| Git hooks | **pre-commit** | Runs all of the above before each commit |

Rules:

- **All configuration lives in `pyproject.toml`**, except `.pre-commit-config.yaml` which pre-commit requires as a separate file.
- **Python 3.12** is the minimum supported version (`requires-python`) and the pinned development version (`.python-version`).
- **Dev tools are a uv dependency group** (`[dependency-groups].dev`), installed by default with `uv sync`. They are not runtime dependencies of the package.
- **Pre-commit hooks for ruff, mypy and pytest are `local` hooks invoking `uv run`**, so the hooks use exactly the versions pinned in `uv.lock` and can never disagree with running the tools by hand.
- **Every public function and test is fully type-annotated**; mypy strict mode enforces this.
- Commands are always run through uv (`uv run pytest`, not `pytest`).

## Consequences

- One command (`uv sync`) gives a reviewer a working environment.
- Code that fails lint, formatting, type checks or tests cannot be committed without explicitly bypassing hooks.
- Strict mypy adds friction with untyped third-party libraries; where needed, overrides are scoped per module in `pyproject.toml` and justified in a comment.
- Running pytest in a pre-commit hook slows commits as the suite grows; if that becomes a problem, it moves to CI via a new ADR.
