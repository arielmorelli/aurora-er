# CLAUDE.md

## Read before doing anything

Before writing or changing any code, read:

1. [`docs/README.md`](docs/README.md) — documentation index
2. Every ADR in [`docs/adr/`](docs/adr/)
3. Every guideline in [`docs/guidelines/`](docs/guidelines/)

These documents are binding. If a request conflicts with them, say so and ask
before proceeding rather than working around them.

## Rules

- **Decisions are documented.** If a change alters project structure, tooling,
  dependencies or the modelling approach, draft a new ADR with status
  *Proposed* and ask the user to accept it. Do not edit accepted ADRs —
  supersede them.
- **Keep the history.** After each step, append bullets to
  [`docs/history.md`](docs/history.md): what was asked, what was decided,
  alternatives considered and any course corrections.
- **Stay in scope.** Do only what was asked. Suggest extra work; don't do it.
- **`docs/input/` is read-only.** It holds the exercise brief and data.
- **Use the Makefile:** `make install`, `make run`, `make test`, `make check`.
  For anything without a target, go through uv (`uv run …`, `uv add …`).
- **Before declaring work done**, run `make check` and make sure it passes.
  Report failures honestly.
- **No AI attribution.** Never add Claude (or any tool) as co-author or
  credit in commits, PRs, comments or docs.
- **Commit messages follow Conventional Commits** (ADR 0004), e.g.
  `feat(battery): add state-of-charge limits`.
- **Every `datetime` is timezone-aware.** Never create or pass a naive one.
- **No hard-coded values.** Every number comes from a DTO; DTO fields have no
  defaults. Only unit conversions may be constants.
- **The solver implements [`docs/problem-definition.md`](docs/problem-definition.md).**
  Every rule must trace back to the brief or the attachments.
- Code is fully typed (mypy strict) and every new behaviour has unit tests.
- **Clean code: docstrings are required, `#` comments only when extremely
  necessary**
  (see [`docs/guidelines/code-style.md`](docs/guidelines/code-style.md)).
