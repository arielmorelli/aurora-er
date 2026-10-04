# Documentation

This folder is the source of truth for how the project is structured and how
work is done in it. Read it before changing code.

| Path | Contents |
| --- | --- |
| [`adr/`](adr/) | Architecture Decision Records — *why* things are the way they are |
| [`guidelines/`](guidelines/) | Day-to-day conventions — *how* to work in the repo |
| [`input/`](input/) | The exercise brief and price data (read-only) |
| [`problem-definition.md`](problem-definition.md) | The dispatch problem: inputs, rules, formulation, output |
| [`history.md`](history.md) | How the project is being built, step by step |

## Architecture Decision Records

| # | Title | Status |
| --- | --- | --- |
| [0001](adr/0001-project-structure-and-ai-usage.md) | Project structure and AI-assisted development | Accepted |
| [0002](adr/0002-python-tooling.md) | Python tooling: uv, ruff, mypy, pytest, pre-commit | Accepted |
| [0003](adr/0003-makefile-as-command-interface.md) | Makefile as the command interface | Accepted |
| [0004](adr/0004-conventional-commits.md) | Conventional Commits | Accepted |
| [0005](adr/0005-dtos-as-frozen-dataclasses.md) | DTOs as frozen dataclasses | Proposed |
| [0006](adr/0006-optimisation-modelling-and-solver.md) | Optimisation modelling and solver | Accepted |
| [0007](adr/0007-battery-dispatch-formulation.md) | Battery dispatch formulation | Accepted |

New ADRs copy [`adr/template.md`](adr/template.md), take the next number, and
are added to the table above.

## Guidelines

- [Development workflow](guidelines/development.md)
- [Code style](guidelines/code-style.md)
