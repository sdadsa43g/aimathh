"""Optimization: known minima + stationarity checks."""

from aimathh.math import optimize as OPT


def test_quadratic_minimum():
    r = OPT.minimize("(x-3)^2", ["x"], [0.0])
    assert abs(r["x"][0] - 3.0) < 1e-6
    assert r["fun"] < 1e-10
    assert r["stationary"] is True


def test_rosenbrock():
    r = OPT.minimize("(1-x)^2 + 100*(y-x^2)^2", ["x", "y"], [0.0, 0.0])
    assert abs(r["x"][0] - 1.0) < 1e-3
    assert abs(r["x"][1] - 1.0) < 1e-3


def test_global_finds_minimum():
    r = OPT.global_minimize("x^2 + (y-2)^2", ["x", "y"], [[-5, 5], [-5, 5]], seed=1)
    assert r["fun"] < 1e-6
    assert r["disagreement"] < 1e-3  # independent global optimizer agrees


def test_sensitivity_quadratic():
    r = OPT.sensitivity("x^2", ["x"], [3.0])
    assert abs(r["sensitivities"]["x"] - 2.0) < 1e-3  # d ln x^2 / d ln x = 2
