# 0001. Project structure and AI-assisted development

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

This repository is the deliverable for a recruitment technical exercise
(see [`docs/input/`](../input/)). The reviewers explicitly assess sensible
design, clear communication of the development process, and a codebase that is
easy to understand and review.

The project is developed with the help of an AI coding assistant (Claude Code).
AI assistants are fast but, without guidance, tend to make undocumented
decisions, drift from conventions, and expand scope. We need the reasoning
behind the codebase to be visible to a human reviewer, and we need the
assistant to follow the same rules a human contributor would.

## Decision

### Repository structure

```
.
├── CLAUDE.md          # Entry point for the AI assistant; points to docs/
├── README.md          # What the project is and how to run it
├── pyproject.toml     # Project metadata and all tool configuration
├── src/aurora_er/     # Package source code (src layout)
├── tests/             # Unit tests
└── docs/
    ├── README.md      # Index of the documentation
    ├── adr/           # Architecture Decision Records
    ├── guidelines/    # Working conventions
    └── input/         # Exercise brief and data — read-only
```

- **src layout.** Code lives under `src/` so tests run against the installed
  package rather than whatever happens to be on the working directory path.
- **`tests/` holds unit tests only.** Integration and end-to-end tests are out
  of scope for now; if introduced, they get their own subfolder and an ADR.
- **`docs/` is the source of truth.** Significant decisions are recorded as
  ADRs (numbered, immutable once accepted — superseded rather than edited).
  Conventions live in `docs/guidelines/`.
- **`docs/input/` is read-only.** The original brief and data are never
  modified, so results are always reproducible from the provided inputs.

### AI-assisted development

- `CLAUDE.md` at the repo root instructs the assistant to read `docs/` before
  making changes and to follow the ADRs and guidelines.
- The assistant does not make significant design decisions silently: anything
  that would warrant an ADR is proposed as one (status *Proposed*) for the
  human author to accept.
- AI-generated changes go through the same gates as human ones: pre-commit
  hooks, type checking, linting and tests (see [ADR 0002](0002-python-tooling.md)).
- The human author remains responsible for every change merged and reviews
  AI output before committing.

## Consequences

- Reviewers can follow *why* the code looks the way it does by reading the ADRs.
- The assistant's behaviour is constrained by versioned, reviewable documents
  rather than ad-hoc prompts.
- Writing ADRs adds a small overhead to each significant decision; this is
  accepted given the exercise rewards clear communication of process.
