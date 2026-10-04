# Documentation

This folder is the source of truth for how the project is structured and how work is done in it. Read it before changing code.

| Path | Contents |
| --- | --- |
| [`adr/`](adr/) | Architecture Decision Records — *why* things are the way they are |
| [`guidelines/`](guidelines/) | Day-to-day conventions — *how* to work in the repo |
| [`problem-definition.md`](problem-definition.md) | The dispatch problem: inputs, rules, formulation, output |
| [`ui-design.md`](ui-design.md) | UI design: tabs, sessions, background runs |
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
| [0007](adr/0007-battery-dispatch-formulation.md) | Battery dispatch formulation | Accepted, partly superseded by 0008 |
| [0008](adr/0008-valuing-battery-wear.md) | Valuing battery wear | Accepted |
| [0009](adr/0009-input-loading-and-run-configuration.md) | Input loading and run configuration | Proposed |
| [0010](adr/0010-rolling-monthly-windows.md) | Rolling monthly windows | Accepted |
| [0011](adr/0011-user-interface-framework.md) | User interface framework | Accepted |
| [0012](adr/0012-window-sizes.md) | Window sizes | Accepted |
| [0013](adr/0013-sessions-and-background-runs.md) | Sessions and background runs | Accepted, runs superseded by 0014 |
| [0014](adr/0014-background-runs-in-processes.md) | Background runs in processes | Accepted |

New ADRs copy [`adr/template.md`](adr/template.md), take the next number, and are added to the table above.

## Guidelines

- [Development workflow](guidelines/development.md)
- [Code style](guidelines/code-style.md)
- [Documentation](guidelines/documentation.md)
