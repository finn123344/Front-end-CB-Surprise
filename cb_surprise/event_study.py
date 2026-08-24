"""Event study of front-end repricing around scored communication events.

Daily resolution: with free data the finest honest window is close-to-close.
An event time-stamped after the local market close is attributed to the next
trading day. All moves are in basis points.

Inference is deliberately simple and robust: heteroskedasticity-robust (HC1)
standard errors on the OLS slope, a sign-agreement hit rate with a binomial
p-value, and a placebo test that reassigns each event to random non-event
days — the placebo R² distribution is what "noise" actually looks like here.
"""

import math

import numpy as np
import pandas as pd

from .config import CHAIR_ROLES, DECISION_EVENT_TYPES, MARKET_MAP, StudyConfig
from .macro import load_calendar


def _locate(index: pd.DatetimeIndex, date: pd.Timestamp) -> int:
    """Position of the first trading day >= date, or -1 if out of range."""
    pos = index.searchsorted(date.normalize())
    return pos if pos < len(index) else -1


def attach_moves(events: pd.DataFrame, yields: pd.DataFrame,
                 cfg: StudyConfig) -> pd.DataFrame:
    """Attach event-day, pre-window and post-window yield changes (bp)."""
    rows = []
    for _, ev in events.iterrows():
        series_name = MARKET_MAP.get(ev["bank"])
        if series_name is None or series_name not in yields.columns:
            continue
        y = yields[series_name].dropna()
        ts = pd.Timestamp(ev["timestamp"])
        close_hour = cfg.market_close_hour.get(ev["bank"], 16)
        eff = ts.normalize() + pd.Timedelta(days=1) if ts.hour >= close_hour else ts.normalize()
        pos = _locate(y.index, eff)
        if pos <= cfg.pre_window or pos < 0 or pos + cfg.post_window >= len(y):
            continue
        rec = ev.to_dict()
        rec["eff_date"] = y.index[pos]
        rec["event_move_bp"] = (y.iloc[pos] - y.iloc[pos - 1]) * 100
        rec["pre_move_bp"] = (y.iloc[pos - 1] - y.iloc[pos - 1 - cfg.pre_window]) * 100
        rec["post_move_bp"] = (y.iloc[pos + cfg.post_window] - y.iloc[pos]) * 100
        rec["is_chair"] = str(ev.get("role", "")).lower() in CHAIR_ROLES
        rows.append(rec)
    return pd.DataFrame(rows)


def ols_r2(x: pd.Series, y: pd.Series) -> dict:
    """One-variable OLS: slope (bp per surprise unit), HC1 standard error,
    t-stat, R² and N."""
    mask = x.notna() & y.notna()
    x, y = x[mask].to_numpy(float), y[mask].to_numpy(float)
    n = len(x)
    if n < 3 or np.ptp(x) == 0:
        return {"n": n, "slope": np.nan, "se": np.nan, "t": np.nan, "r2": np.nan}
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - (resid ** 2).sum() / ss_tot if ss_tot > 0 else np.nan
    xc = x - x.mean()
    sxx = (xc ** 2).sum()
    se = math.sqrt((xc ** 2 * resid ** 2).sum() * n / max(n - 2, 1)) / sxx
    t = slope / se if se > 0 else np.nan
    return {"n": n, "slope": slope, "se": se, "t": t, "r2": r2}


def hit_rate(surprise: pd.Series, move: pd.Series) -> dict:
    """Fraction of events where the move's sign matches the surprise's sign,
    with a two-sided binomial p-value against a coin flip (normal approx)."""
    mask = surprise.notna() & move.notna() & (surprise != 0) & (move != 0)
    n = int(mask.sum())
    if n == 0:
        return {"n": 0, "rate": np.nan, "p": np.nan}
    hits = int((np.sign(surprise[mask]) == np.sign(move[mask])).sum())
    z = (hits - n / 2) / math.sqrt(n / 4)
    p = math.erfc(abs(z) / math.sqrt(2))
    return {"n": n, "rate": hits / n, "p": p}


def placebo_r2(ev: pd.DataFrame, yields: pd.DataFrame,
               n_iter: int = 500, seed: int = 0) -> np.ndarray:
    """Placebo distribution: keep the surprises, replace each event's move
    with a random daily move from the same market. Returns n_iter R² values —
    what the headline regression produces when the dates carry no information."""
    rng = np.random.default_rng(seed)
    pools = {s: yields[s].dropna().diff().dropna().to_numpy() * 100
             for s in yields.columns}
    series = ev["bank"].map(MARKET_MAP).to_numpy()
    surp = ev["surprise"].to_numpy(float)
    groups = {s: np.flatnonzero(series == s) for s in np.unique(series)}
    out = np.empty(n_iter)
    moves = np.empty(len(ev))
    for i in range(n_iter):
        for s, idx in groups.items():
            pool = pools[s]
            moves[idx] = pool[rng.integers(0, len(pool), len(idx))]
        r = np.corrcoef(surp, moves)[0, 1]
        out[i] = r * r
    return out


def abs_move_distribution(moves: pd.Series, percentiles=(50, 75, 90, 95)) -> dict:
    a = moves.abs().dropna()
    out = {"n": len(a), "mean": a.mean()}
    out.update({f"p{p}": np.percentile(a, p) for p in percentiles} if len(a) else {})
    return out


def non_event_moves(yields: pd.DataFrame, events: pd.DataFrame) -> pd.Series:
    """Daily changes (bp) on days with no scored event, pooled across the
    mapped markets — the control the event days are judged against."""
    event_days = set(pd.to_datetime(events["timestamp"]).dt.normalize())
    pooled = []
    for col in yields.columns:
        d = yields[col].dropna().diff().mul(100).dropna()
        pooled.append(d[~d.index.normalize().isin(event_days)])
    return pd.concat(pooled)


def run_study(events: pd.DataFrame, yields: pd.DataFrame,
              cfg: StudyConfig | None = None,
              placebo_iters: int = 500) -> dict:
    """Full study: returns the event table with moves plus summary stats."""
    cfg = cfg or StudyConfig()
    ev = attach_moves(events, yields, cfg)
    if ev.empty or ev["surprise"].notna().sum() == 0:
        raise ValueError(
            "no usable events: check that banks appear in MARKET_MAP, that the "
            "yield series covers the event dates, and that speakers have enough "
            "prior scored events for a surprise to be defined")
    ev = ev[ev["surprise"].notna()].copy()
    if "event_type" not in ev.columns:
        ev["event_type"] = "speech"

    # flag events whose market day coincides with a major macro release
    calendar = load_calendar(ev["eff_date"].min(), ev["eff_date"].max())
    ev["macro_day"] = ev["eff_date"].isin(calendar)
    # scheduled decision days: presser move is confounded with the decision
    ev["is_decision"] = ev["event_type"].str.lower().isin(DECISION_EVENT_TYPES)

    # magnitude buckets: terciles of |surprise| (ties can collapse the edges,
    # in which case bucketing is meaningless and everything is "all")
    try:
        ev["mag_bucket"] = pd.qcut(ev["surprise"].abs(), 3,
                                   labels=["small", "medium", "large"])
    except ValueError:
        ev["mag_bucket"] = "all"

    clean = ev[~ev["macro_day"]]
    speeches = ev[~ev["is_decision"] & ~ev["macro_day"]]
    ne_moves = non_event_moves(yields, events)

    results = {
        "events": ev,
        "n_events": len(ev),
        # How much does the surprise explain of the event-day move?
        "event_day": ols_r2(ev["surprise"], ev["event_move_bp"]),
        # ...excluding macro-release days (the confound-controlled headline)
        "event_day_clean": ols_r2(clean["surprise"], clean["event_move_bp"]),
        # ...speeches only: the clean identification, no statement in the window
        "event_day_speeches": ols_r2(speeches["surprise"], speeches["event_move_bp"]),
        "hit_rate": hit_rate(ev["surprise"], ev["event_move_bp"]),
        # Was it already in the price? Pre-window move vs eventual surprise.
        "pre_positioning": ols_r2(ev["surprise"], ev["pre_move_bp"]),
        # Post-event drift (should be ~0 if repricing is immediate).
        "post_drift": ols_r2(ev["surprise"], ev["post_move_bp"]),
        "dist_all": abs_move_distribution(ev["event_move_bp"], cfg.width_percentiles),
        "dist_chair": abs_move_distribution(
            ev.loc[ev["is_chair"], "event_move_bp"], cfg.width_percentiles),
        "dist_regional": abs_move_distribution(
            ev.loc[~ev["is_chair"], "event_move_bp"], cfg.width_percentiles),
        "dist_non_event": abs_move_distribution(ne_moves, cfg.width_percentiles),
        "non_event_moves": ne_moves,
        "by_magnitude": {
            str(b): abs_move_distribution(g["event_move_bp"], cfg.width_percentiles)
            for b, g in ev.groupby("mag_bucket", observed=True)
        },
    }

    if placebo_iters and len(ev) >= 30:
        pr2 = placebo_r2(ev, yields, n_iter=placebo_iters)
        real = results["event_day"]["r2"]
        results["placebo"] = {
            "n_iter": placebo_iters,
            "median_r2": float(np.median(pr2)),
            "p_value": float((pr2 >= real).mean()),
        }
    return results
