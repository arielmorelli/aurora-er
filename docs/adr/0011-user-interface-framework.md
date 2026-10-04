# 0011. User interface framework

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

The project needs a UI on top of the existing Python code. This ADR chooses the framework only; how the UI looks and behaves is decided separately.

Criteria for the framework:

- **Python only:** no separate frontend stack or build step.
- **Light:** installs with `uv` as a regular dependency.
- **Components:** form inputs, file upload, data tables and charts available out of the box.
- **Long-running calls:** a full run of the model takes minutes, so the framework must cope with calls that take that long.
- **Fits the project rules:** works with mypy strict, and UI code can be tested in pytest without a browser.
- **Readable by reviewers:** familiar enough that a reviewer can follow the UI code quickly.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| **Streamlit** | Fastest to build; widgets, file upload, data tables and charts built in; very widely known; ships type hints; `AppTest` runs an app headless in pytest. | Re-runs the whole script on each interaction, so long-running calls need care; limited layout control. |
| NiceGUI | Event-driven (no script re-runs), so long-running work is natural; FastAPI underneath; pytest fixtures for UI tests. | Smaller community, less familiar to reviewers; more code for tables and charts. |
| Gradio | Very light, typed, good for "inputs → function → outputs". | Built for ML demos; dashboards with several tables and charts are awkward. |
| Dash (Plotly) | Strong interactive charts; explicit callbacks. | More boilerplate; browser-based testing (Selenium) is heavy. |
| Panel (HoloViz) | Powerful, flexible layouts, reactive. | Larger API surface; heavier for a small app. |
| Shiny for Python | Clean reactive model; good testing story. | Less common in Python; smaller ecosystem. |
| marimo | Reactive notebook that runs as an app; pure Python files. | Notebook-shaped; younger project. |
| FastAPI + HTMX / React | Full control. | A web stack to build and test; far beyond the exercise's scope. |

## Decision

Use **Streamlit**: it meets every criterion with built-in components, it is the most widely known option, and `AppTest` allows browser-free tests. Its re-run model is a known constraint that the UI design has to account for.

NiceGUI is the fallback if Streamlit's re-run model becomes a real obstacle.

## Consequences

- One new runtime dependency (`streamlit`).
- The UI is a new composition root reusing the loaders, solver and report; no modelling logic moves into it.
- UI design (layout, inputs, outputs, run behaviour) is decided separately.
