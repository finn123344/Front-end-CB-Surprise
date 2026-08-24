"""Same-day macro-release control.

A daily close-to-close window attributes the whole day to the event, so a
speech on a payrolls or CPI day inherits the data move — the headline
regressions must be reported with and without those days.

Two sources combine:

- a deterministic rule for US nonfarm payrolls (first Friday of the month;
  correct in the vast majority of months — list exceptions in the CSV),
- an optional ``data/macro_releases.csv`` (columns: ``date, release``) for
  CPI, euro-area flash releases, and anything else worth excluding.
  Official calendars: bls.gov/schedule and the Eurostat release calendar.
"""

from pathlib import Path

import pandas as pd

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "macro_releases.csv"


def nfp_dates(start, end) -> pd.DatetimeIndex:
    """First Friday of every month in [start, end]."""
    firsts = pd.period_range(start, end, freq="M").to_timestamp()
    fridays = firsts + pd.to_timedelta((4 - firsts.dayofweek) % 7, unit="D")
    return pd.DatetimeIndex(fridays[(fridays >= pd.Timestamp(start))
                                    & (fridays <= pd.Timestamp(end))])


def load_calendar(start, end, csv_path: Path | None = None) -> pd.DatetimeIndex:
    """NFP rule plus whatever the optional release CSV adds."""
    dates = set(nfp_dates(start, end))
    path = DEFAULT_CSV if csv_path is None else Path(csv_path)
    if path.exists():
        extra = pd.read_csv(path, parse_dates=["date"])
        dates |= set(extra["date"].dt.normalize())
    return pd.DatetimeIndex(sorted(dates))
