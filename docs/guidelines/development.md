# Development workflow

Rationale: [ADR 0002](../adr/0002-python-tooling.md) (tooling),
[ADR 0003](../adr/0003-makefile-as-command-interface.md) (Makefile),
[ADR 0004](../adr/0004-conventional-commits.md) (commit messages).

## Setup

```bash
make install
```

## Everyday commands

| Task | Command |
| --- | --- |
| List targets | `make` |
| Run the model | `make run` |
| Run tests | `make test` |
| Run every quality gate (lint, format, types, tests) | `make check` |

Less frequent tasks, run directly through uv:

| Task | Command |
| --- | --- |
| Run tests with coverage | `uv run pytest --cov=aurora_er` |
| Add a runtime dependency | `uv add <package>` |
| Add a dev dependency | `uv add --dev <package>` |

## Conventions

- Source code goes in `src/aurora_er/`; unit tests in `tests/`, named
  `test_<module>.py`.
- Every new behaviour comes with unit tests.
- `make check` passes before every commit.
- Commit messages follow Conventional Commits, e.g.
  `feat(battery): add state-of-charge limits` (see ADR 0004).
- Never hand-edit `uv.lock`; change dependencies through `uv add` / `uv remove`.
- Never modify files in `docs/input/`.
- A change that alters structure, tooling or the modelling approach needs an ADR
  (copy [`adr/template.md`](../adr/template.md)).
