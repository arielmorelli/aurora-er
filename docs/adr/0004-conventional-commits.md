# 0004. Conventional Commits

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

The exercise is assessed partly on how clearly the development process is communicated. The git history is part of that story, so commit messages must be consistent and meaningful, whether written by a human or by the AI assistant.

## Decision

Commit messages follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>(<optional scope>): <description>

<optional body>

<optional footer(s)>
```

Allowed types:

| Type | Use for |
| --- | --- |
| `feat` | New behaviour in the package |
| `fix` | Bug fix |
| `docs` | Documentation only (README, ADRs, guidelines) |
| `test` | Adding or changing tests only |
| `refactor` | Code change that neither fixes a bug nor adds behaviour |
| `perf` | Performance improvement |
| `build` | Dependencies, `pyproject.toml`, `uv.lock`, Makefile |
| `ci` | CI configuration |
| `chore` | Maintenance that fits nothing above (e.g. pre-commit config) |
| `style` | Formatting only, no behaviour change |
| `revert` | Reverting a previous commit |

Rules:

- Description in the imperative mood, lower case, no trailing period, ≤ 72 characters including the prefix: `feat(market): load half-hourly prices`.
- Scope is optional; when used, it names the area touched (e.g. `battery`, `market`, `adr`).
- The body explains *why* when it isn't obvious from the description.
- Breaking changes use `!` after the type/scope and a `BREAKING CHANGE:` footer.
- One logical change per commit.
- Enforced by the `conventional-pre-commit` hook at the `commit-msg` stage, installed by `make install`.

## Consequences

- History is scannable by type, and changelogs could be generated later.
- Non-conforming messages are rejected at commit time; fixing one means re-running the commit with a corrected message.
