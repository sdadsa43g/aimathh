"""Numerical differentiation & integration (SciPy-backed)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import integrate, optimize


def _make_fn(expr: str, var: str = "x"):
    import sympy as sp

    e = sp.sympify(expr)
    return sp.lambdify(sp.Symbol(var), e, "numpy")


def quad(expr: str, a: float, b: float, var: str = "x", tol: float = 1e-10) -> dict[str, Any]:
    f = _make_fn(expr, var)
    val, abserr = integrate.quad(f, a, b, epsabs=tol, epsrel=tol)
    # Independent route: fixed high-order Gauss-Legendre
    xs, ws = np.polynomial.legendre.leggauss(200)
    mid, half = (a + b) / 2, (b - a) / 2
    indep = float(np.sum(ws * f(mid + half * xs)) * half)
    return {
        "expression": expr,
        "interval": [a, b],
        "value": float(val),
        "estimated_abs_error": float(abserr),
        "independent_gauss_legendre": indep,
        "disagreement": abs(float(val) - indep),
    }


def dblquad(expr: str, ax: float, bx: float, ay: float, by_: float, vars: list[str] | None = None) -> dict[str, Any]:
    import sympy as sp

    vars = vars or ["x", "y"]
    e = sp.sympify(expr)
    f = sp.lambdify([sp.Symbol(v) for v in vars], e, "numpy")
    val, err = integrate.dblquad(lambda y, x: float(f(x, y)), ax, bx, ay, by_)
    return {"value": float(val), "estimated_abs_error": float(err)}


def derivative(expr: str, point: float, var: str = "x", order: int = 1) -> dict[str, Any]:
    """Numerical derivative with step-size convergence study (stability check)."""
    f = _make_fn(expr, var)
    hs = [1e-2, 1e-3, 1e-4, 1e-5, 1e-6]
    ests: list[float] = []
    for h in hs:
        if order == 1:
            ests.append(float((f(point + h) - f(point - h)) / (2 * h)))
        elif order == 2:
            ests.append(float((f(point + h) - 2 * f(point) + f(point - h)) / h**2))
        else:
            raise ValueError("Only first/second derivatives supported numerically")
    # Convergence: last two estimates should agree to ~sqrt(h) level
    conv = abs(ests[-2] - ests[-1])
    scale = max(1.0, abs(ests[-1]))
    return {
        "expression": expr,
        "point": point,
        "order": order,
        "steps": hs,
        "estimates": ests,
        "value": ests[-2],
        "convergence_gap": conv,
        "stable": bool(conv / scale < 1e-4),
    }


def find_root(expr: str, a: float, b: float, var: str = "x") -> dict[str, Any]:
    f = _make_fn(expr, var)
    fa, fb = float(f(a)), float(f(b))
    bracketed = fa == 0 or fb == 0 or (fa < 0) != (fb < 0)
    if not bracketed:
        raise ValueError(f"Root not bracketed: f({a})={fa}, f({b})={fb}")
    sol = optimize.brentq(f, a, b, full_output=True)
    root = float(sol[0])
    return {"root": root, "f_root": float(f(root)), "iterations": int(sol[1].iterations)}
