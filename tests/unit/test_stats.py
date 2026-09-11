"""Statistics + Monte Carlo convergence."""

from aimathh.math import stats as ST


def test_describe():
    r = ST.describe([1, 2, 3, 4, 5])
    assert r["mean"] == 3.0
    assert r["median"] == 3.0
    assert r["n"] == 5


def test_linregress_exact_line():
    r = ST.linregress([0, 1, 2, 3], [1, 3, 5, 7])
    assert abs(r["slope"] - 2.0) < 1e-12
    assert abs(r["r_squared"] - 1.0) < 1e-12


def test_monte_carlo_mean():
    r = ST.monte_carlo("x", ["x"], {"x": {"dist": "uniform", "low": 0.0, "high": 1.0}}, n=50000, seed=0)
    assert abs(r["mean"] - 0.5) < 0.01
    assert r["converged"] is True


def test_beta_binomial():
    r = ST.bayes_beta_binomial(8, 10)
    assert 0.5 < r["mean"] < 0.9
    assert r["ci95"][0] < r["mean"] < r["ci95"][1]
