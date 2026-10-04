# Known limitations

Behaviour that is simplified or not modelled, by design or for lack of time. Each item says what happens today.

## Inputs

- **Price units are not read.** Prices are always taken as £/MWh, whatever the unit in the price column's header says. A sheet in €/MWh or £/kWh is used as if it were £/MWh, with no warning.
- **Timestamps are trusted by position.** Each price sheet is read as consecutive intervals from its first timestamp, in UTC. Rows whose timestamp does not match their position are reported but used by position; missing or extra rows are not detected as such.

## Battery model

- **A replacement keeps the stored energy.** It is an instant swap with no downtime: the energy in the old battery carries over, and cycles and degradation restart from zero.
- **Battery value is linear in cycles.** It ignores calendar age and the volume already lost to degradation.
- **Tie at the cycle limit.** A battery that ends a window exactly at its lifetime cycles may or may not be replaced at the last boundary: the replacement costs the capex and restores the same value, so both are optimal.
- **A battery replaced for cycles does not also age out in the same horizon.** Validation keeps each solve within one calendar lifetime so this cannot happen.

## Rolling windows

- **Stored energy has no value at a window end,** so each window tends to end with the battery empty; shorter windows lose more. See the open question in the [problem definition](problem-definition.md#open-questions).
- **Windows do not see each other's prices.** Each window is optimal on its own; the whole horizon is not proven optimal.

## Web UI

- **Runs depend on the app.** Each run is a child process of the Streamlit app on the local machine, so if the app stops or crashes, its running sessions stop too; they show as interrupted the next time the app starts.
- **Cancel takes effect after the current window,** not immediately.
- **The result charts are basic.** The History page shows market profit per window as a bar chart; it is kept to show how similar the windows' results are, not as an analysis tool (no prices, dispatch or stored-energy charts).

How these would be addressed in production, and the modelling next steps, are in [`production-architecture.md`](production-architecture.md).
