import numpy as np
import pandas as pd

from cb_surprise.event_study import hit_rate, ols_r2, placebo_r2


def test_ols_recovers_a_clean_slope():
    rng = np.random.default_rng(1)
    x = pd.Series(rng.normal(0, 1, 400))
    y = 3.0 * x + pd.Series(rng.normal(0, 0.5, 400))
    fit = ols_r2(x, y)
    assert abs(fit["slope"] - 3.0) < 0.15
    assert fit["t"] > 20           # unambiguous signal -> large t
    assert 0.9 < fit["r2"] <= 1.0


def test_ols_null_has_small_t():
    rng = np.random.default_rng(2)
    x = pd.Series(rng.normal(0, 1, 400))
    y = pd.Series(rng.normal(0, 1, 400))
    assert abs(ols_r2(x, y)["t"]) < 3


def test_hit_rate_perfect_and_null():
    x = pd.Series([-2.0, -1.0, 1.0, 2.0] * 25)
    perfect = hit_rate(x, x * 5)
    assert perfect["rate"] == 1.0 and perfect["p"] < 1e-6
    anti = hit_rate(x, -x)
    assert anti["rate"] == 0.0


def test_placebo_r2_is_noise_scale():
    rng = np.random.default_rng(3)
    idx = pd.bdate_range("2020-01-01", periods=600)
    yields = pd.DataFrame({"US2Y": pd.Series(rng.normal(0, 0.04, 600), index=idx).cumsum()})
    ev = pd.DataFrame({
        "bank": ["FED"] * 60,
        "surprise": rng.normal(0, 1, 60),
    })
    r2s = placebo_r2(ev, yields, n_iter=50, seed=0)
    assert r2s.shape == (50,)
    assert (r2s >= 0).all() and (r2s <= 1).all()
    assert np.median(r2s) < 0.1    # random pairing explains ~nothing
