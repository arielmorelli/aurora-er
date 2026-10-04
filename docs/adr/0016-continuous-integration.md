# 0016. Continuous integration

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

Quality gates (ruff, mypy strict, pytest) run locally through pre-commit ([ADR 0002](0002-python-tooling.md)) and `make check` ([ADR 0003](0003-makefile-as-command-interface.md)). Hooks can be skipped or not installed, so nothing guarantees that what reaches GitHub passes them. The author asked for a CI step that runs the tests and `make check`.

## Decision

- **GitHub Actions**, in `.github/workflows/ci.yml`, on every pull request and every push to `main`.
- One job on Ubuntu: install uv (with its cache), `uv sync --locked`, then `make test` and `make check`. Using the `make` targets keeps CI identical to what a developer runs locally.
- `uv sync --locked` fails if `uv.lock` is out of date with `pyproject.toml`, so CI installs exactly the locked versions.
- The pre-commit hook environments are cached by the hash of `.pre-commit-config.yaml`.
- A newer push to the same branch cancels the previous run.
- No deployment step: the project has no environment to deploy to. In the production design ([`production-architecture.md`](../production-architecture.md)), CD would build and publish the API and worker images after this job passes.

## Consequences

- A pull request shows whether it passes every quality gate before it is merged; branch protection on `main` can require the job.
- `make check` already runs pytest, so the tests run twice per job; the separate `make test` step makes a test failure easy to spot in the job log, at the cost of a little time.
