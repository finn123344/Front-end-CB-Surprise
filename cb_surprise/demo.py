"""Synthetic demo data so the pipeline runs end-to-end without the private
scored-events archive or network access.

Everything produced here is FAKE and labeled as such. It is calibrated to the
shape the real study is expected to show — most communication is already in
the price, event-day R² is low, chair events move more than regional
speeches — so the demo exercises the honest-null reporting path, not a
fantasy result.
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(7)

SPEAKERS = [
    # bank, speaker, role, base hawkishness, events/year, beta (bp per unit surprise)
    ("FED", "Chair",        "chair",    0.0,  14, 16.0),
    ("FED", "Riverside",    "regional", 0.8,  10, 3.0),
    ("FED", "Lakeshore",    "regional", -0.6, 10, 3.0),
    ("FED", "Hillcrest",    "regional", 0.3,   8, 3.0),
    ("ECB", "President",    "president", 0.0, 12, 13.0),
    ("ECB", "Northgate",    "regional", 1.0,   9, 2.5),
    ("ECB", "Southbay",     "regional", -0.9,  9, 2.5),
]

START, END = "2016-01-01", "2025-12-31"
PRICED_IN = 0.7   # share of the surprise absorbed in the pre-window
DAILY_VOL_BP = {"US2Y": 4.0, "EA2Y": 3.0}


def make_events() -> pd.DataFrame:
    """Scored events: score = speaker base level + slow policy cycle + noise."""
    days = pd.date_range(START, END, freq="D")
    cycle = np.cumsum(RNG.normal(0, 0.02, len(days)))  # common policy mood
    cycle = pd.Series(cycle - cycle.mean(), index=days)
    rows = []
    for bank, speaker, role, base, per_year, beta in SPEAKERS:
        n = int(per_year * 10)
        dates = pd.to_datetime(sorted(RNG.choice(days[days.dayofweek < 5], n, replace=False)))
        for d in dates:
            score = base + cycle[d] + RNG.normal(0, 0.5)
            hour = int(RNG.choice([10, 13, 14, 15]))
            rows.append({
                "timestamp": d + pd.Timedelta(hours=hour),
                "bank": bank, "speaker": speaker, "role": role,
                "event_type": "presser" if role in ("chair", "president") else "speech",
                "score": round(score, 3), "_beta": beta,
            })
    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)


def make_yields(events: pd.DataFrame) -> pd.DataFrame:
    """Random-walk 2y series with the surprise partially pre-priced: PRICED_IN
    of each event's effect leaks in over the 5 prior days, the rest hits on
    the event day. The event-day signal is small relative to daily vol, which
    is what produces the realistic low R²."""
    from .surprise import add_surprise
    from .config import MARKET_MAP

    ev = add_surprise(events)
    idx = pd.bdate_range(START, END)
    out = {}
    for series, vol in DAILY_VOL_BP.items():
        shocks = RNG.normal(0, vol / 100, len(idx))
        out[series] = pd.Series(shocks, index=idx)
    for _, e in ev.dropna(subset=["surprise"]).iterrows():
        series = MARKET_MAP.get(e["bank"])
        if series is None:
            continue
        effect = e["_beta"] * e["surprise"] / 100  # percent
        pos = idx.searchsorted(pd.Timestamp(e["timestamp"]).normalize())
        if pos < 6 or pos >= len(idx):
            continue
        out[series].iloc[pos - 5:pos] += PRICED_IN * effect / 5
        out[series].iloc[pos] += (1 - PRICED_IN) * effect
    levels = {k: 1.5 + v.cumsum() for k, v in out.items()}
    return pd.DataFrame(levels)
