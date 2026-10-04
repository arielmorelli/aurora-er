# 0012. Window sizes

- **Status:** Accepted; the `3 months` size removed by [0015](0015-remove-three-month-windows.md)
- **Date:** 2026-10-04
- **Amends:** [ADR 0010](0010-rolling-monthly-windows.md) — windows are no longer months only

## Context

ADR 0010 split long horizons into calendar-month windows. The author asked for the UI to let users choose the window size: a day, a week, a month or three months.

## Decision

- `WindowSize` has four values: `day`, `week`, `month` and `3 months`. It replaces `months_per_window` in `RunConfig`.
- **Day and week** windows are fixed lengths of real time (24 h, 7 days) counted from the horizon start, so every window but the last has the same length, whatever the weekday or clock changes.
- **Month and 3 months** follow calendar months in the horizon's timezone, as in ADR 0010.
- Windows are still solved in order and chained through the battery state; everything else in ADR 0010 holds.

## Consequences

- Shorter windows solve faster but see less of the future, so they tend to earn less; longer windows see more but take longer. Users can compare.
- Each window still ends with the battery empty (no value for stored energy at a window end), which costs more with shorter windows.
