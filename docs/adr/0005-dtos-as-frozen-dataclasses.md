# 0005. DTOs as frozen dataclasses

- **Status:** Proposed
- **Date:** 2026-10-04

## Context

The exercise inputs (`docs/input/`) describe the battery and the market prices.
Those shapes will cross the transport layer (whatever reads input and writes
results), so they need a typed, stable representation that is independent of
the source format — the spreadsheets are only the reference for the fields,
not something the DTOs know about.

## Decision

- DTOs live in `src/aurora_er/dto/`, one module per concept.
- Each DTO is a `@dataclass(frozen=True, slots=True, kw_only=True)`:
  - `frozen` — immutable and hashable; safe to pass around and cache.
  - `slots` — no accidental attributes, smaller instances.
  - `kw_only` — construction is explicit, so fields of the same type
    (e.g. charge and discharge rates) cannot be swapped by position.
- DTOs carry data only: no behaviour, no validation, no parsing. Validation
  and domain rules belong to the layers that consume them.
- Field names carry their unit as a suffix (`_mw`, `_mwh`, `_gbp`,
  `_gbp_per_year`, `_fraction`, `_pct_per_cycle`) because the inputs mix units
  and percent-vs-fraction conventions.
- Where the source label is misleading, the field is named for what the value
  means. Renames from `Attachment 1.xlsx`:

  | Source label | Field | Why |
  | --- | --- | --- |
  | Battery charging efficiency | `charging_loss_fraction` | Value (0.05) is the fraction lost |
  | Battery discharging efficiency | `discharging_loss_fraction` | Value (0.05) is the fraction lost |
  | Lifetime (1) | `lifetime_years` | Disambiguates by unit |
  | Lifetime (2) | `lifetime_cycles` | Disambiguates by unit |
  | Storage volume degradation rate | `degradation_rate_pct_per_cycle` | Value is in %, not a fraction |
- Standard library only — no pydantic/attrs dependency.

## Consequences

- DTOs are trivially constructible in tests and type-checked by mypy strict.
- Any input validation must be written explicitly elsewhere; a DTO can hold
  nonsensical values (e.g. a negative capacity).
- If runtime validation at the boundary becomes necessary, a new ADR can
  revisit pydantic.
