# Project history

How the project is being built, step by step: what was asked, what was
decided, and what changed along the way. Formal decisions live in
[ADRs](adr/); this is the narrative around them. Newest entries at the bottom.

## 2026-10-04

### 1. Project scaffold

- Started from the exercise brief and data in `docs/input/` (battery dispatch
  across two wholesale markets).
- Chose a src-layout Python package (`src/aurora_er/`) with unit tests in
  `tests/`; integration and e2e tests left out of scope.
- Made `docs/` the source of truth and added `CLAUDE.md` so the AI assistant
  reads the docs before changing anything → [ADR 0001](adr/0001-project-structure-and-ai-usage.md).
- uv, ruff, mypy, pytest and pre-commit were a fixed requirement, so they were
  recorded as a single decision → [ADR 0002](adr/0002-python-tooling.md).
- Python 3.12 picked as minimum to match the local interpreter (uv defaulted
  to 3.14).
- mypy runs in strict mode; pre-commit hooks call `uv run` so they use the
  versions pinned in `uv.lock`.

### 2. Makefile and commit convention

- Added a Makefile as the single command interface: `make install`, `run`,
  `test`, `check` → [ADR 0003](adr/0003-makefile-as-command-interface.md).
- `make check` delegates to pre-commit, so the local check and the commit hook
  are the same thing.
- `make run` needed a target, so a placeholder `python -m aurora_er` entry point
  was added.
- Adopted Conventional Commits, enforced by a `commit-msg` hook
  → [ADR 0004](adr/0004-conventional-commits.md).
- First commit: `chore: scaffold project structure, tooling and ADRs`.

### 3. Battery parameters DTO

- Modelled `Attachment 1.xlsx` as `BatterySpecDTO`: a frozen dataclass used as
  a DTO for the future transport layer, independent of the xlsx format
  → [ADR 0005](adr/0005-dtos-as-frozen-dataclasses.md) (Proposed).
- Options considered: field names mirroring the sheet vs. unit-suffixed names;
  `dto/` vs. `transport/` package. Chose unit-suffixed names in `dto/`.
- The sheet labels charging/discharging "efficiency" but the values (0.05) are
  losses, so the fields became `charging_loss_fraction` /
  `discharging_loss_fraction`.
- `kw_only=True` so same-typed fields (e.g. charge vs. discharge rate) can't be
  swapped positionally.

### 4. Code style

- First stated as "clean code, comments only when extremely necessary"; all
  comments and docstrings were removed.
- Clarified: **docstrings are required, only `#` comments are restricted**.
  Docstrings were restored → [code style guideline](guidelines/code-style.md).

### 5. Market DTO

- Modelled Market 2 (`Attachment 2.xlsx`, hourly sheet) as `MarketDTO`, generic
  enough to also hold Market 1 (half-hourly).
- Requirement: a horizon (start inclusive, end exclusive) and a step length.
  Prices are a plain tuple; the price at index `i` covers the interval starting
  at `horizon_start + i * step_length`.
- Added `name` to tell markets apart.
- Data inspection found timestamp quirks to handle in the loader, not the DTO:
  - Market 2: 6 timestamps a few milliseconds off the hour (Excel float
    precision), e.g. `2020-12-31 22:59:59.994`.
  - Market 1: 3 gaps of 90 min and 3 steps back of 30 min (likely DST
    artefacts).
  - The fixed grid (start + step) lets the loader snap to it rather than trust
    each timestamp.
