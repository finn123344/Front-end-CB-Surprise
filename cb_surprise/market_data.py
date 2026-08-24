"""Free daily 2y-yield data: FRED (US) and the ECB Data Portal (euro area).

Both endpoints are keyless. Downloads are cached as CSV under data/cache/ so
the study is reproducible offline after the first run.
"""

from io import StringIO
from pathlib import Path

import pandas as pd
import requests

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
ECB_CSV = (
    "https://data-api.ecb.europa.eu/service/data/YC/"
    "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y?format=csvdata&startPeriod={start}"
)


def _cached(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{name}.csv"


def fetch_us2y(start: str = "2014-01-01", refresh: bool = False) -> pd.Series:
    """Daily 2y constant-maturity Treasury yield (FRED: DGS2), percent."""
    cache = _cached("US2Y")
    if refresh or not cache.exists():
        r = requests.get(FRED_CSV.format(series="DGS2"), timeout=60)
        r.raise_for_status()
        cache.write_text(r.text)
    df = pd.read_csv(cache, na_values=".")
    df.columns = ["date", "yield"]
    s = df.set_index(pd.to_datetime(df["date"]))["yield"].dropna()
    return s.loc[start:].rename("US2Y")


def fetch_ea2y(start: str = "2014-01-01", refresh: bool = False) -> pd.Series:
    """Daily euro-area AAA 2y spot yield (ECB Data Portal YC dataset), percent."""
    cache = _cached("EA2Y")
    if refresh or not cache.exists():
        r = requests.get(ECB_CSV.format(start=start), timeout=120)
        r.raise_for_status()
        cache.write_text(r.text)
    df = pd.read_csv(cache)
    s = df.set_index(pd.to_datetime(df["TIME_PERIOD"]))["OBS_VALUE"].dropna()
    return s.loc[start:].rename("EA2Y")


FETCHERS = {"US2Y": fetch_us2y, "EA2Y": fetch_ea2y}


def load_yields(series_names, start: str = "2014-01-01", refresh: bool = False) -> pd.DataFrame:
    """Fetch (or read from cache) each requested series; returns a wide DataFrame."""
    out = {}
    for name in series_names:
        if name not in FETCHERS:
            raise KeyError(f"No fetcher registered for series '{name}'")
        out[name] = FETCHERS[name](start=start, refresh=refresh)
    return pd.DataFrame(out)
