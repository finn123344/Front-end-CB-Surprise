# Findings

> **SYNTHETIC DEMO DATA** — these numbers exercise the pipeline; they are not a result.

- Events with a defined surprise: **698**
- Event-day repricing vs surprise: slope **2.1 bp/unit**, **R² = 0.094** (n = 698)
- Pre-positioning (move over the 5 prior days vs eventual surprise): slope 6.6 bp/unit, R² = 0.150
- Post-event drift vs surprise: slope 0.3 bp/unit, R² = 0.003

## Distribution of |event-day move| and quote widths (bp)

| class            |    n |   breakeven_bp |   p50 |   p75 |   p90 |   p95 |
|:-----------------|-----:|---------------:|------:|------:|------:|------:|
| all events       |  698 |           3.21 |  2.73 |  4.47 |  6.6  |  7.9  |
| chair / presser  |  253 |           3.41 |  3.04 |  4.66 |  6.8  |  8.11 |
| regional / other |  445 |           3.1  |  2.6  |  4.32 |  6.49 |  7.81 |
| non-event day    | 3964 |           2.85 |  2.31 |  4.16 |  5.98 |  7.12 |

## |move| by surprise-magnitude bucket

- small: n=233, mean 2.9 bp, p90 6.1 bp
- medium: n=232, mean 3.2 bp, p90 6.8 bp
- large: n=233, mean 3.5 bp, p90 6.9 bp
