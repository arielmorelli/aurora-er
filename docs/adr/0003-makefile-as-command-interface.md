# 0003. Makefile as the command interface

- **Status:** Accepted; `make run` replaced by `make run-example` in [0009](0009-input-loading-and-run-configuration.md), then reintroduced to start the UI in [0013](0013-sessions-and-background-runs.md)
- **Date:** 2026-10-04

## Context

[ADR 0002](0002-python-tooling.md) standardises on uv and several tools, each with its own invocation. Contributors and reviewers should not need to remember those invocations: there should be one short, discoverable command per task.

## Decision

A `Makefile` at the repo root is the single entry point for common tasks. Its targets are thin wrappers around `uv run …`; tool configuration stays in `pyproject.toml` and `.pre-commit-config.yaml`.

| Target | Does | Runs |
| --- | --- | --- |
| `make install` | Create the environment and install git hooks | `uv sync` + `uv run pre-commit install` |
| `make run` | Run the battery dispatch model | `uv run python -m aurora_er` |
| `make test` | Run the unit tests | `uv run pytest` |
| `make check` | Run every quality gate on all files | `uv run pre-commit run --all-files` |
| `make` / `make help` | List targets | — |

Rules:

- Documentation (README, guidelines) refers to `make` targets, not raw commands.
- `make check` delegates to pre-commit so the local check and the commit hook are identical by construction.
- New targets are added only when a task is repeated often; each gets a `## ` description so it appears in `make help`.

## Consequences

- Onboarding is `make install`; verifying a change is `make check`.
- Requires GNU Make, which is available by default on Linux and macOS. Windows users need WSL or can run the underlying `uv` commands directly.
- The Makefile is a second place where commands live; keeping targets as one-line wrappers keeps that duplication trivial.
