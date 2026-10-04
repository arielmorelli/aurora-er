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
- Tests are named for the behaviour they check and need no docstring.

## Comments

Code explains itself through names and structure. Inline `#` comments are
written only when extremely necessary.

- No comments that describe *what* the code does — rename or extract instead.
- A comment is acceptable only for a *why* that the code cannot express: a
  non-obvious constraint, a workaround, or a deliberate deviation from the
  expected approach.
- Decision context belongs in ADRs, not in comments.

## Naming

- Names say what a thing is, including units for physical or monetary
  quantities: `max_storage_volume_mwh`, `capex_gbp`.
- Prefer a longer precise name over a short name plus a comment.
- Test helpers and fixtures are named for the scenario they build
  (`_attachment_1_spec`), not generically (`_spec`, `data`).

## Functions and modules

- Small functions that do one thing.
- One concept per module.
