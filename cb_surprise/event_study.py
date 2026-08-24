"""Event study of front-end repricing around scored communication events.

Daily resolution: with free data the finest honest window is close-to-close.
An event time-stamped after the local market close is attributed to the next
trading day. All moves are in basis points.
"""

import numpy as np
import pandas as pd

from .config import CHAIR_ROLES, MARKET_MAP, StudyConfig


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
        rec["event_move_bp"] = (y.iloc[pos] - y.iloc[pos - 1]) * 100
        rec["pre_move_bp"] = (y.iloc[pos - 1] - y.iloc[pos - 1 - cfg.pre_window]) * 100
        rec["post_move_bp"] = (y.iloc[pos + cfg.post_window] - y.iloc[pos]) * 100
        rec["is_chair"] = str(ev.get("role", "")).lower() in CHAIR_ROLES
        rows.append(rec)
    return pd.DataFrame(rows)


def ols_r2(x: pd.Series, y: pd.Series) -> dict:
    """Slope (bp per surprise unit), R² and N of a one-variable OLS."""
    mask = x.notna() & y.notna()
    x, y = x[mask].to_numpy(float), y[mask].to_numpy(float)
    if len(x) < 3 or np.ptp(x) == 0:
        return {"n": len(x), "slope": np.nan, "r2": np.nan}
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - (resid ** 2).sum() / ss_tot if ss_tot > 0 else np.nan
    return {"n": len(x), "slope": slope, "r2": r2}


def abs_move_distribution(moves: pd.Series, percentiles=(50, 75, 90, 95)) -> dict:
    a = moves.abs().dropna()
    out = {"n": len(a), "mean": a.mean()}
    out.update({f"p{p}": np.percentile(a, p) for p in percentiles} if len(a) else {})
    return out


def non_event_baseline(yields: pd.DataFrame, events: pd.DataFrame,
                       percentiles=(50, 75, 90, 95)) -> dict:
    """Distribution of |daily change| on days with no scored event, pooled
    across the mapped markets — the control the event days are judged against."""
    event_days = set(pd.to_datetime(events["timestamp"]).dt.normalize())
    pooled = []
    for col in yields.columns:
        d = yields[col].dropna().diff().mul(100).dropna()
        pooled.append(d[~d.index.normalize().isin(event_days)])
    return abs_move_distribution(pd.concat(pooled), percentiles)


def run_study(events: pd.DataFrame, yields: pd.DataFrame,
              cfg: StudyConfig | None = None) -> dict:
    """Full study: returns the event table with moves plus summary stats."""
    cfg = cfg or StudyConfig()
    ev = attach_moves(events, yields, cfg)
    ev = ev[ev["surprise"].notna()].copy()

    # magnitude buckets: terciles of |surprise|
    if len(ev) >= 9:
        ev["mag_bucket"] = pd.qcut(ev["surprise"].abs(), 3,
                                   labels=["small", "medium", "large"])
    else:
        ev["mag_bucket"] = "all"

    results = {
        "events": ev,
        "n_events": len(ev),
        # How much does the surprise explain of the event-day move?
        "event_day": ols_r2(ev["surprise"], ev["event_move_bp"]),
        # Was it already in the price? Pre-window move vs eventual surprise.
        "pre_positioning": ols_r2(ev["surprise"], ev["pre_move_bp"]),
        # Post-event drift (should be ~0 if repricing is immediate).
        "post_drift": ols_r2(ev["surprise"], ev["post_move_bp"]),
        "dist_all": abs_move_distribution(ev["event_move_bp"], cfg.width_percentiles),
        "dist_chair": abs_move_distribution(
            ev.loc[ev["is_chair"], "event_move_bp"], cfg.width_percentiles),
        "dist_regional": abs_move_distribution(
            ev.loc[~ev["is_chair"], "event_move_bp"], cfg.width_percentiles),
        "dist_non_event": non_event_baseline(yields, events, cfg.width_percentiles),
        "by_magnitude": {
            str(b): abs_move_distribution(g["event_move_bp"], cfg.width_percentiles)
            for b, g in ev.groupby("mag_bucket", observed=True)
        },
    }
    return results
