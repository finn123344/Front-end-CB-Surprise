"""Speaker-relative surprise: deviation of a score from the speaker's own
trailing mean, not from zero.

A permanently hawkish regional president saying something hawkish is not news;
the same words from a speaker who usually sits at the dovish end are. This is
the computation that requires the scored archive.
"""

import pandas as pd


def add_surprise(events: pd.DataFrame, trailing_window: int = 8,
                 min_prior_events: int = 3) -> pd.DataFrame:
    """Append 'baseline' and 'surprise' columns.

    events must have: timestamp (tz-aware or naive UTC), bank, speaker, score.
    The baseline for each event is the mean of the same speaker's previous
    `trailing_window` scores (strictly before the event — no lookahead).
    Events with fewer than `min_prior_events` prior scores get surprise = NaN
    and are excluded downstream.
    """
    df = events.sort_values("timestamp").copy()
    grp = df.groupby(["bank", "speaker"], sort=False)["score"]
    baseline = grp.transform(
        lambda s: s.shift(1).rolling(trailing_window, min_periods=min_prior_events).mean()
    )
    df["baseline"] = baseline
    df["surprise"] = df["score"] - df["baseline"]
    return df
