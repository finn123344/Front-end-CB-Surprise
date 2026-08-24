# Findings

> **SYNTHETIC DEMO DATA** — these numbers exercise the pipeline; they are not a result.

Events with a defined surprise: **698** (34 on macro-release days, 253 on scheduled decision days).

## Does the surprise move the front end?

| sample | n | slope (bp/unit) | HC1 se | t | R² |
|---|---|---|---|---|---|
| event day, all events | 698 | 2.08 | 0.25 | 8.45 | 0.094 |
| event day, ex macro-release days | 664 | 2.10 | 0.25 | 8.43 | 0.098 |
| event day, speeches only ex macro | 420 | 0.97 | 0.29 | 3.37 | 0.022 |
| pre-window (already in the price) | 698 | 6.55 | 0.66 | 9.87 | 0.150 |
| post-event drift | 698 | 0.35 | 0.23 | 1.53 | 0.003 |

- Hit rate (sign of move matches sign of surprise): **61.6%** of 698 events, two-sided p = 8.7e-10.
- Placebo (500 draws of random non-event days, same surprises): median placebo R² = 0.0007; fraction of placebos beating the real R² = **0.000**.

## How wide do you quote? (bp half-widths)

`breakeven` is the always-informed floor E[|move|]; `w(α)` assumes a share α of uninformed flow and informed traders who only cross when the move clears your width.

| class            |    n |   breakeven (bp) |   p50 |   p90 |   p95 |   w(α=0.3) |   w(α=0.5) |   w(α=0.7) |
|:-----------------|-----:|-----------------:|------:|------:|------:|-----------:|-----------:|-----------:|
| all events       |  698 |             3.21 |  2.73 |  6.6  |  7.9  |       2.72 |       1.75 |       0.99 |
| chair / presser  |  253 |             3.41 |  3.04 |  6.8  |  8.11 |       2.87 |       1.85 |       1.05 |
| regional / other |  445 |             3.1  |  2.6  |  6.49 |  7.81 |       2.63 |       1.69 |       0.96 |
| non-event day    | 3964 |             2.85 |  2.31 |  5.98 |  7.12 |       2.47 |       1.56 |       0.88 |

## |move| by surprise-magnitude bucket

- small: n=233, mean 2.9 bp, p90 6.1 bp
- medium: n=232, mean 3.2 bp, p90 6.8 bp
- large: n=233, mean 3.5 bp, p90 6.9 bp
