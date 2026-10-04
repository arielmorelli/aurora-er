# 0008. Valuing battery wear

- **Status:** Accepted
- **Date:** 2026-10-04
- **Supersedes:** the "Battery lifetime and degradation" costing in [ADR 0007](0007-battery-dispatch-formulation.md)

## Context

ADR 0007 charged `capex_gbp` only when a battery reached its end of life. Within a horizon shorter than the battery's life, cycles were therefore free: the replacement they bring closer falls after the horizon.

The first real-data run (first week of January 2018, Attachment 1 battery) showed the effect:

| | Market profit | Cycles |
| --- | --- | --- |
| No cycle cap | £1,239.53 | 21.6 |
| Cycle pace cap | £1,109.84 | 9.6 |

The extra 12 cycles earned ~£10.80 each, while each cycle consumes `capex_gbp / lifetime_cycles` = £100 of battery life. The uncapped dispatch maximised market profit at a large hidden cost; the cap limited it but only through an externally imposed budget, without weighing profit against wear.

## Decision

- The installed battery has a **value** proportional to its remaining cycles: `capex_gbp × (lifetime_cycles − cycles_used) / lifetime_cycles`.
- The objective adds the **battery value at the end of the horizon**, so every cycle costs `capex_gbp / lifetime_cycles`. The solver cycles only when the price spread, after losses, pays for that wear.
- The replacement rule of ADR 0007 is kept: a cycle-driven replacement pays `capex_gbp` and restores the same value (nets to zero); a calendar replacement writes off the value the old battery still had.
- The result reports the battery value at the start and end of the horizon, and `net_profit_gbp` includes the change, so a run that wears the battery out no longer looks profitable.
- The cycle pace cap stays as an option for comparison.

## Alternatives considered

- **Keep cycles free, rely on the cap.** Gives the best profit for a fixed cycle budget, but the budget is arbitrary and the trade-off is never made.
- **Cost per cycle as an assumed parameter.** Mathematically the same price per cycle; rejected in ADR 0007 as an assumption. Here the price is derived from capex and lifetime cycles, both inputs, as the replacement cost spread over the cycles that consume it.
- **Optimise over the full battery life.** Would capture the trade-off directly, but the data covers three years and the model would be far larger.

## Consequences

- The dispatch is no longer myopic about wear; cycling falls on the real data.
- Profit reporting separates cash (capex, opex) from the value consumed.
- Value ignores calendar age and capacity already lost to degradation; both are documented limitations.
