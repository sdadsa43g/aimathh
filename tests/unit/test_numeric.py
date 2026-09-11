"""Arbitrary-precision numerics: exact digits + stability flags."""

from aimathh.math import numeric as N


def test_sqrt2_fifty_digits():
    r = N.evaluate("sqrt(2)", {}, 50)
    # 50 significant digits of sqrt(2)
    assert r["value"].startswith("1.4142135623730950488016887242096980785696718753769")
    assert r["stable"] is True


def test_sin_pi_6():
    r = N.evaluate("sin(pi/6)", {}, 25)
    assert abs(float(r["value"]) - 0.5) < 1e-24
    assert r["relative_disagreement"] < 1e-20


def test_constants():
    c = N.constants(50)
    # 50 significant digits of pi
    assert c["pi"].startswith("3.1415926535897932384626433832795028841971693993751")


def test_high_precision_quad():
    r = N.quad_high_precision("sin(x)", "x", 0.0, 3.141592653589793, 25)
    assert abs(float(r["value"]) - 2.0) < 1e-20
    assert r["stable"] is True
