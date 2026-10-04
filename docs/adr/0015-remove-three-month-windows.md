# 0015. Remove three-month windows

- **Status:** Accepted
- **Date:** 2026-10-04
- **Supersedes:** the `3 months` window size in [ADR 0012](0012-window-sizes.md)

## Context

[ADR 0012](0012-window-sizes.md) offered four window sizes: a day, a week, a month and three months. Solve time grows much faster than the horizon: a month solves in seconds, while a quarter did not finish in 10 minutes when measured for [ADR 0010](0010-rolling-monthly-windows.md). A three-month window therefore risks hitting the time limit and returning a non-optimal plan, for little gain.

## Decision

- The author removed the `3 months` window size. `WindowSize` has `day`, `week` and `month`.
- Everything else in ADR 0012 holds: days and weeks are fixed lengths from the horizon start, months follow calendar months.

## Consequences

- Every window size offered solves in reasonable time.
- Sessions saved with `window_size: 3 months` can no longer be read; the History page shows an error for them instead of their details.
