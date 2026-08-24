"""The one bug that silently fakes a result is lookahead in the baseline."""

import pandas as pd

from cb_surprise.surprise import add_surprise


def _events(scores):
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=len(scores), freq="7D"),
        "bank": "FED", "speaker": "X", "role": "regional", "score": scores,
    })


def test_baseline_excludes_current_score():
    ev = add_surprise(_events([1.0, 1.0, 1.0, 9.0]), trailing_window=8, min_prior_events=3)
    last = ev.iloc[-1]
    assert last["baseline"] == 1.0          # mean of the three PRIOR scores only
    assert last["surprise"] == 8.0


def test_min_prior_events_gates_early_surprises():
    ev = add_surprise(_events([1.0, 2.0, 3.0, 4.0]), trailing_window=8, min_prior_events=3)
    assert ev["surprise"].isna().tolist() == [True, True, True, False]


def test_trailing_window_caps_history():
    scores = [0.0] * 8 + [10.0] * 8 + [10.0]
    ev = add_surprise(_events(scores), trailing_window=8, min_prior_events=3)
    # baseline of the last event sees only the eight 10.0s, not the old 0.0s
    assert ev.iloc[-1]["baseline"] == 10.0


def test_speakers_do_not_share_baselines():
    a = _events([1.0, 1.0, 1.0, 1.0])
    b = _events([5.0, 5.0, 5.0, 5.0]).assign(speaker="Y")
    ev = add_surprise(pd.concat([a, b]), trailing_window=8, min_prior_events=3)
    assert ev.loc[ev["speaker"] == "Y", "surprise"].iloc[-1] == 0.0
