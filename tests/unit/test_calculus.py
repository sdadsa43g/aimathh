"""Numerical differentiation/integration/root-finding."""

from aimathh.math import calculus as C


def test_quad_sin():
    r = C.quad("sin(x)", 0, 3.141592653589793)
    assert abs(r["value"] - 2.0) < 1e-9
    assert r["disagreement"] < 1e-9  # independent Gauss-Legendre agrees


def test_derivative_converges():
    r = C.derivative("exp(x)", 1.0)
    import math

    assert abs(r["value"] - math.e) < 1e-6
    assert r["stable"] is True


def test_second_derivative():
    r = C.derivative("sin(x)", 0.5, order=2)
    import math

    assert abs(r["value"] + math.sin(0.5)) < 1e-4


def test_root():
    r = C.find_root("x^2-2", 1.0, 2.0)
    assert abs(r["root"] - 1.4142135623730951) < 1e-10
    assert abs(r["f_root"]) < 1e-10
