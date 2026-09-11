"""ODE solver: exact-solution agreement + cross-method checks."""

import math

from aimathh.math import ode as O


def test_exponential_decay_matches_exact():
    sol = O.solve_ivp(["-y"], ["y"], [0, 1], [1.0], n_points=50)
    assert sol["agree"] is True
    assert abs(sol["y_primary"][0][-1] - math.exp(-1)) < 1e-6


def test_harmonic_oscillator_period():
    # x'' = -x  =>  x(2pi) = x(0) = 1
    sol = O.solve_ivp(["v", "-x"], ["x", "v"], [0, 2 * math.pi], [1.0, 0.0], n_points=200)
    assert sol["agree"] is True
    assert abs(sol["y_primary"][0][-1] - 1.0) < 1e-5
    assert abs(sol["y_primary"][1][-1]) < 1e-5


def test_reports_methods():
    sol = O.solve_ivp(["1"], ["y"], [0, 1], [0.0], n_points=10)
    assert sol["methods"]["primary"] != sol["methods"]["check"]  # genuinely independent routes
