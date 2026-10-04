# Code style

The project follows clean code principles. Formatting and lint rules are
enforced by ruff ([ADR 0002](../adr/0002-python-tooling.md)); this page covers
what tools can't enforce.

## Docstrings

Docstrings are required: they are the public documentation of the code.

- Every module, public class and public function has a docstring.
- Public dataclass fields have an attribute docstring describing meaning and
  unit, and any non-obvious mapping from the source data.
- Docstrings describe *what* and *why* for a caller, not *how* it's implemented.
- Code inside docstrings and comments uses single backticks (`name`), never
  reST double backticks or roles.
- Tests are named for the behaviour they check and need no docstring.

## Comments

Code explains itself through names and structure. Inline `#` comments are
written only when extremely necessary.

- No comments that describe *what* the code does — rename or extract instead.
- A comment is acceptable only for a *why* that the code cannot express: a
  non-obvious constraint, a workaround, or a deliberate deviation from the
  expected approach.
- Decision context belongs in ADRs, not in comments.

## No hard-coded values

- Every number the model uses comes from an input DTO
  ([ADR 0007](../adr/0007-battery-dispatch-formulation.md)).
- DTO fields have no default values; callers pass every field explicitly.
- The only constants allowed in code are unit conversions (e.g. seconds per
  hour, percent to fraction).

## Time

- Every `datetime` is timezone-aware. Naive datetimes are never created,
  stored or passed between modules.
- Use `datetime.UTC` or `zoneinfo.ZoneInfo`; never `datetime.now()` or
  `datetime(...)` without `tzinfo`.
- Data sources without a zone (e.g. spreadsheet cells) get one attached at the
  boundary where they are read, and the zone is documented there.

## Naming

- Names say what a thing is, including units for physical or monetary
  quantities: `max_storage_volume_mwh`, `capex_gbp`.
- Prefer a longer precise name over a short name plus a comment.
- Test helpers and fixtures are named for the scenario they build
  (`_attachment_1_spec`), not generically (`_spec`, `data`).

## Dependency injection

- Functions and classes receive their collaborators as arguments (solver
  backend, data source, clock, writer) instead of creating or importing them
  internally.
- Tests pass fakes or small real instances through those arguments; no
  monkeypatching of module globals.
- Wiring the real collaborators together happens in one place, at the entry
  point.

## Functions and modules

- Small functions that do one thing.
- One concept per module.
