"""Transforms + nonlinear systems."""

import math

from aimathh.math import nonlinear as NL
from aimathh.math import transforms as T


def test_laplace_exp():
    r = T.laplace_symbolic("exp(-a*t)", "t", "s")
    assert "s" in r["transform"] and "a" in r["transform"]


def test_fft_peak():
    sig = [math.sin(2 * math.pi * 5 * t / 100) for t in range(200)]
    r = T.fft_spectrum(sig, 0.01)
    assert abs(r["peak_freq"] - 5.0) < 0.6


def test_nonlinear_sqrt2():
    r = NL.solve_nonlinear(["x^2-2"], ["x"], [1.0])
    assert abs(r["x"][0] - math.sqrt(2)) < 1e-10
    assert r["verified"] is True


def test_stability_stable_node():
    r = NL.fixed_point_stability(["-x", "-2*y"], ["x", "y"], [0.0, 0.0])
    assert r["is_fixed_point"] is True
    assert r["stability"] == "asymptotically stable"


def test_vector_field_shape():
    f = NL.vector_field(["y", "-x"], ["x", "y"], {"x": [-1, 1], "y": [-1, 1]}, n=10)
    assert len(f["x"]) == 10 and len(f["u"]) == 10 and len(f["u"][0]) == 10
