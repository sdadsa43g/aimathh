"""Counterexample engine refutes false universals, spares true ones (bounded)."""

from aimathh.verification import get_counterexample_engine

eng = get_counterexample_engine()


def test_refutes_false_claim():
    # Claim: x^2 - 3x + 2 >= 0 for x in [0, 3] — FALSE (roots at 1 and 2).
    rep = eng.attack("x^2-3*x+2", ["x"], {"x": [0, 3]}, n_random=2000)
    assert rep["status"] == "refuted"
    x = rep["counterexample"]["x"]
    assert 1.0 < x < 2.0  # between the roots, where the polynomial is negative


def test_refutes_sin_claim():
    # Claim: sin(x) >= 0.5 on [0, 2pi] — obviously false.
    rep = eng.attack("sin(x)", ["x"], {"x": [0, 6.283185307179586]}, threshold=0.5, n_random=2000)
    assert rep["status"] == "refuted"


def test_no_counterexample_for_true_claim():
    # x^2 + 1 >= 1 everywhere — true; bounded search must not hallucinate one.
    rep = eng.attack("x^2+1", ["x"], {"x": [-5, 5]}, threshold=1.0, n_random=3000)
    assert rep["status"] == "no_counterexample_found"
    assert "NOT a proof" in rep["note"]
