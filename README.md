# aurora-er

A Python package that models a battery charging and discharging across two
wholesale electricity markets to maximise profit. Built as a technical exercise
for a recruitment process — the original brief and data live in
[`inputs/`](inputs/).

- **Market 1** — half-hourly prices (£/MWh)
- **Market 2** — hourly prices (£/MWh)

> 🚧 Work in progress. This README will be expanded with the modelling
> approach, how to run the model, and reproducible results.

## Quick start

Requires [uv](https://docs.astral.sh/uv/) and GNU Make.

```bash
make install       # create .venv, install dependencies and git hooks
make run-example   # read inputs/, solve 2018–2020 month by month, print results
make test          # run the unit tests
make check         # lint, format, type-check and test everything
```

## Project layout

```
src/aurora_er/   # package source code
tests/           # unit tests
inputs/          # exercise brief and data (read-only)
docs/            # ADRs, guidelines and history — start here
```

See [`docs/README.md`](docs/README.md) for the architecture decisions and
development guidelines that govern this repository.
