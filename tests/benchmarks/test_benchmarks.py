"""Benchmark suite: known math/physics problems with exact expected answers.

Each benchmark runs the full MODEL->PLAN->COMPUTE->VERIFY path (tools +
verification engine) and asserts the exact answer. A separate adversarial
section feeds WRONG model outputs to the verification engine and asserts
they are REJECTED — the harness must catch errors, not just compute.
"""

import math

import pytest

from aimathh.core.types import VerificationStatus
from aimathh.math import calculus as C
from aimathh.math import linalg as L
from aimathh.math import numeric as N
from aimathh.math import ode as O
from aimathh.math import optimize as OPT
from aimathh.math import symbolic as S
from aimathh.physics.dimensional import check_equation
from aimathh.verification import get_counterexample_engine, get_verification_engine

eng = get_verification_engine()


# ---- exact-answer benchmarks ----------------------------------------------
@pytest.mark.parametrize(("expr", "expected"), [
    ("2+2", "4"),
    ("sin(pi/2)", "1"),
    ("diff(x^3,x)", "3*x**2"),
])
def test_bench_symbolic_exact(expr, expected):
    if expr.startswith("diff("):
        r = S.differentiate("x^3", "x", variables=["x"])["derivative"]
    else:
        r = S.simplify_expr(expr)["simplified"]
    assert r == expected


def test_bench_integral_x2_0_to_1():
    assert S.integrate("x^2", "x", "0", "1", ["x"])["result"] == "1/3"


def test_bench_sqrt2_30_digits():
    v = N.evaluate("sqrt(2)", {}, 30)["value"]
    assert v.startswith("1.41421356237309504880168872421")


def test_bench_linear_system():
    r = L.solve_linear([[3, 1], [1, 2]], [9, 8])
    assert all(abs(a - b) < 1e-12 for a, b in zip(r["x"], [2.0, 3.0]))


def test_bench_quad_cos():
    r = C.quad("cos(x)", 0, math.pi / 2)
    assert abs(r["value"] - 1.0) < 1e-10


def test_bench_ode_decay():
    sol = O.solve_ivp(["-2*y"], ["y"], [0, 1], [1.0], n_points=50)
    assert abs(sol["y_primary"][0][-1] - math.exp(-2)) < 1e-6


def test_bench_optimizer_minimum():
    r = OPT.minimize("(x+1)^2+(y-2)^2", ["x", "y"], [5.0, -5.0])
    assert abs(r["x"][0] + 1.0) < 1e-5 and abs(r["x"][1] - 2.0) < 1e-5


def test_bench_kepler_dimensional():
    assert check_equation(
        "T^2 = 4*pi^2*a^3/(G*M)",
        {"T": "s", "a": "m", "G": "m^3/(kg s^2)", "M": "kg", "pi": "dimensionless"}).consistent


def test_bench_projectile_range():
    # R = v^2 sin(2θ)/g ; v=10, θ=45°, g=9.80665 -> R = 100/9.80665
    r = N.evaluate("v^2*sin(2*theta)/g", {"v": "10", "theta": str(math.pi / 4), "g": "9.80665"}, 20)
    assert abs(float(r["value"]) - 100 / 9.80665) < 1e-12


# ---- adversarial: verification must REJECT wrong model outputs -------------
def test_adversarial_wrong_identity_rejected():
    vr = eng.verify_claim("model: (a+b)^2 = a^2+b^2",
                          [eng.symbolic_equal("(a+b)^2", "a^2+b^2", ["a", "b"])])
    assert vr.status == VerificationStatus.FAILED


def test_adversarial_wrong_number_rejected():
    vr = eng.verify_claim("model: sqrt(2) = 1.5",
                          [eng.high_precision_confirm("sqrt(2)", {}, 1.5, dps=30)])
    assert vr.status == VerificationStatus.FAILED


def test_adversarial_bad_physics_rejected():
    vr = eng.verify_claim("model: E = m c",
                          [eng.dimensional("E = m*c", {"E": "joule", "m": "kg", "c": "m/s"})])
    assert vr.status == VerificationStatus.FAILED


def test_adversarial_false_universal_refuted():
    rep = get_counterexample_engine().attack("x^3 - 2*x + 1", ["x"], {"x": [-2, 2]},
                                             relation=">=", threshold=0.0, n_random=3000)
    assert rep["status"] == "refuted"  # f(-2) = -3 < 0


def test_adversarial_close_but_wrong_number_rejected():
    # pi != 3.1416 at 1e-6 tolerance
    assert eng.numeric_agree(3.1416, math.pi, tol=1e-6).status == VerificationStatus.FAILED
