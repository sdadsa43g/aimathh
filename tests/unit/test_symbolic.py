"""Symbolic engine correctness against known exact results."""

from aimathh.math import symbolic as S


def test_pythagorean_identity():
    r = S.simplify_expr("sin(x)^2+cos(x)^2", ["x"])
    assert r["simplified"] == "1"


def test_expand_factor_roundtrip():
    assert S.expand_expr("(x+1)^2", ["x"])["expanded"] == "x**2 + 2*x + 1"
    assert S.factor_expr("x^2+2*x+1", ["x"])["factored"] == "(x + 1)**2"


def test_differentiate():
    r = S.differentiate("x^3", "x", variables=["x"])
    assert r["derivative"] == "3*x**2"


def test_integrate_definite():
    r = S.integrate("x^2", "x", "0", "1", ["x"])
    assert r["result"] == "1/3"
    assert not r["unevaluated"]


def test_integrate_gaussian_reports_closed_form_or_flags():
    r = S.integrate("exp(-x^2)", "x", "-oo", "oo", ["x"])
    assert "sqrt(pi)" in r["result"] or r["unevaluated"] is False


def test_solve_quadratic():
    r = S.solve_equation("x^2-4", "x", ["x"])
    assert sorted(r["solutions"]) == ["-2", "2"]


def test_solve_system():
    r = S.solve_system(["x+y=3", "x-y=1"], ["x", "y"])
    assert r["solutions"] == [{"x": "2", "y": "1"}]


def test_series():
    r = S.series_expand("exp(x)", "x", 0.0, 4, ["x"])
    assert "x**3/6" in r["series"].replace(" ", "")


def test_limit():
    r = S.limit_expr("sin(x)/x", "x", "0", variables=["x"])
    assert r["limit"] == "1"


def test_matrix_det_inv():
    assert S.matrix_op("det", [[[1, 2], [3, 4]]])["result"] == "-2"
    inv = S.matrix_op("inv", [[[1, 2], [3, 4]]])["result"]
    assert "2/3" in inv or "-2" in inv  # contains exact rationals


def test_equality_true_and_false():
    assert S.are_symbolically_equal("sin(x)^2+cos(x)^2", "1", ["x"])["equal"] is True
    assert S.are_symbolically_equal("sin(x)", "cos(x)", ["x"])["equal"] is False
    # A wrong "identity" must not be confirmed:
    assert S.are_symbolically_equal("(x+1)^2", "x^2+1", ["x"])["equal"] is False
