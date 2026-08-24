"""The market-maker's version of the question: given the empirical distribution
of front-end moves around an event, how wide do you quote?

Two widths per event class, in increasing realism:

1. **Always-informed floor** — every fill into the event is informed and
   trades regardless of your width: pnl = w − |move|, so break-even
   w = E[|move|]. The most conservative flat assumption.
2. **Mixture width w(α)** — a share α of flow is uninformed (pays you w);
   the informed remainder only hits you when the move clears your width,
   costing |move| − w. Break-even solves
       α·w = (1−α)·E[(|move| − w)⁺]
   against the empirical distribution (bisection; the left side is increasing
   and the right side decreasing in w, so the root is unique). As α → 0 the
   width blows out toward the worst observed move — which is exactly why a
   desk with no uninformed flow shouldn't be quoting into a presser at all.

The chair-vs-regional difference then reads directly as a difference in
quoted width at the same α.
"""

import numpy as np
import pandas as pd


def mixture_width(moves: pd.Series, alpha: float, tol: float = 1e-6) -> float:
    """Break-even half-width w (bp) solving alpha*w = (1-alpha)*E[(|m|-w)+]."""
    a = pd.Series(moves).abs().dropna().to_numpy(float)
    if len(a) == 0 or not 0 < alpha <= 1:
        return np.nan
    lo, hi = 0.0, float(a.max())
    f = lambda w: alpha * w - (1 - alpha) * np.mean(np.maximum(a - w, 0.0))
    if f(hi) <= 0:
        return hi
    for _ in range(100):
        mid = (lo + hi) / 2
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


def quote_table(results: dict, alphas=(0.3, 0.5, 0.7)) -> pd.DataFrame:
    """One row per event class: distribution widths plus mixture widths (bp)."""
    ev = results["events"]
    classes = [
        ("all events", ev["event_move_bp"]),
        ("chair / presser", ev.loc[ev["is_chair"], "event_move_bp"]),
        ("regional / other", ev.loc[~ev["is_chair"], "event_move_bp"]),
        ("non-event day", results["non_event_moves"]),
    ]
    rows = []
    for label, moves in classes:
        a = moves.abs().dropna()
        if not len(a):
            continue
        rows.append({
            "class": label,
            "n": len(a),
            "breakeven (bp)": round(a.mean(), 2),
            "p50": round(np.percentile(a, 50), 2),
            "p90": round(np.percentile(a, 90), 2),
            "p95": round(np.percentile(a, 95), 2),
            **{f"w(α={al})": round(mixture_width(a, al), 2) for al in alphas},
        })
    return pd.DataFrame(rows)
