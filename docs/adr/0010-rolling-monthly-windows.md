# 0010. Rolling monthly windows

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

The MILP solves one week in ~1 s and one month in ~5 s, but a quarter did not
finish in 10 minutes: solve time grows much faster than the horizon. The
provided data covers three years.

## Decision

- The horizon is split into **calendar-month windows** (the author's choice),
  in the timezone of the horizon start; `months_per_window` in the run config
  sets how many months each window spans. The first and last windows may be
  partial months.
- Windows are solved **in order and do not overlap**. Each starts from the
  previous window's `final_state` (stored energy, cycles used, commissioning
  date), so cycles, degradation and replacements carry across windows.
- `solve` is unchanged; `solve_rolling` wraps it and returns a
  `RollingDispatchResultDTO` with every window's result and totals. Net profit
  is the sum of window net profits: each window's end battery value is the
  next window's start value, so the values telescope.
- The final state is clamped to its physical bounds before it is passed on,
  so solver tolerances cannot make the next window's input invalid.
- Progress is reported through an injected callback after each window.

## Alternatives considered

- **One model for the whole horizon.** Optimal across months, but does not
  solve in reasonable time.
- **Overlapping windows with look-ahead** (solve a month plus some days, keep
  only the month). Avoids end-of-window effects; more solve time and more
  logic. Left as a future improvement.
- **Fixed-length windows** (e.g. 30 days). Simpler arithmetic, but calendar
  months match how results are usually reported.

## Consequences

- The full three years solve in minutes, window by window.
- Each window is optimal on its own; the whole horizon is not proven optimal,
  so the summary reports "every window optimal", not "optimal".
- Stored energy has no value at a window end (open question in the problem
  definition), so each month tends to end with the battery empty. Look-ahead
  or a terminal value for stored energy would address this.
