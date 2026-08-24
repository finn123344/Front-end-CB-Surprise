import pandas as pd

from cb_surprise.macro import nfp_dates


def test_first_friday_rule():
    d = nfp_dates("2024-01-01", "2024-12-31")
    # spot-check months where the 1st falls on different weekdays
    assert pd.Timestamp("2024-11-01") in d   # Nov 1 2024 is itself a Friday
    assert pd.Timestamp("2024-03-01") in d   # Mar 1 2024 is a Friday
    assert pd.Timestamp("2024-09-06") in d   # Sep 1 2024 is a Sunday
    assert len(d) == 12
    assert all(t.dayofweek == 4 for t in d)


def test_range_is_respected():
    d = nfp_dates("2024-06-15", "2024-08-31")
    # June's first Friday (June 7) precedes the start date and must not appear
    assert d.min() >= pd.Timestamp("2024-06-15")
    assert list(d) == [pd.Timestamp("2024-07-05"), pd.Timestamp("2024-08-02")]
