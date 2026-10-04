# Results

Recorded results of `make run-example`, kept as a point-in-time record: they change whenever the model or its inputs change. Run `make run-example` to reproduce the current figures.

## 2026-10-04

- **Code:** commit `93f67c6`
- **Run:** the provided data, 2018-01-01 to 2021-01-01, an empty new battery commissioned at the start, monthly windows, no cycle pace cap, every window solved to proven optimality.

| | £ |
| --- | ---: |
| Market profit | 124,949.62 |
| Capex | −500,000.00 |
| Opex | −15,000.00 |
| Battery value left (701.39 of 5,000 cycles used) | +429,861.02 |
| **Net profit** | **39,810.64** |

| Market | Charged MWh | Discharged MWh | Profit £ |
| --- | ---: | ---: | ---: |
| Market 1 | 2,522.08 | 100.67 | −54,513.98 |
| Market 2 | 431.14 | 2,564.61 | 179,463.60 |

Almost all of the profit comes from buying in Market 1 and selling in Market 2. Two runs gave identical figures.
