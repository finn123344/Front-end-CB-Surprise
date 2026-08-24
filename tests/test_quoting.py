import numpy as np
import pandas as pd

from cb_surprise.quoting import mixture_width


def test_point_mass_closed_form():
    # all |moves| = 10: alpha*w = (1-alpha)*(10-w) has closed form
    moves = pd.Series([10.0] * 100)
    # alpha = 0.5 -> w = 5
    assert abs(mixture_width(moves, 0.5) - 5.0) < 1e-4
    # alpha = 0.25 -> 0.25w = 0.75(10-w) -> w = 7.5
    assert abs(mixture_width(moves, 0.25) - 7.5) < 1e-4


def test_width_decreases_with_more_uninformed_flow():
    rng = np.random.default_rng(0)
    moves = pd.Series(np.abs(rng.normal(0, 5, 500)))
    widths = [mixture_width(moves, a) for a in (0.2, 0.5, 0.8)]
    assert widths[0] > widths[1] > widths[2] > 0


def test_degenerate_inputs():
    assert np.isnan(mixture_width(pd.Series(dtype=float), 0.5))
    assert np.isnan(mixture_width(pd.Series([1.0]), 0.0))
