"""The market-maker's version of the question: given the empirical distribution
of front-end moves around an event, how wide do you quote?

Model: you show a two-way price going into the event and cannot re-quote until
after it. If every fill is informed, quoting half-width w earns w - |move| per
trade, so the break-even width is E[|move|] under the empirical distribution.
That is the floor; a desk that wants to survive the tail quotes nearer the p90
of |move|. Both are reported per event class, so the chair-vs-regional
difference reads directly as a difference in quoted width.
"""

import numpy as np
import pandas as pd


def quote_table(results: dict) -> pd.DataFrame:
    """One row per event class: break-even width and percentile widths (bp)."""
    rows = []
    for label, key in [("all events", "dist_all"),
                       ("chair / presser", "dist_chair"),
                       ("regional / other", "dist_regional"),
                       ("non-event day", "dist_non_event")]:
        d = results[key]
        if not d.get("n"):
            continue
        rows.append({
            "class": label,
            "n": d["n"],
            "breakeven_bp": round(d["mean"], 2),
            **{k: round(v, 2) for k, v in d.items() if k.startswith("p")},
        })
    return pd.DataFrame(rows)
