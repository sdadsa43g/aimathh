"""Optimization: gradient, constrained, global, least-squares, sensitivity."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import optimize


def _make_scalar_fn(expr: str, variables: list[str]):
    import sympy as sp

    e = sp.sympify(expr)
    syms = [sp.Symbol(v) for v in variables]
    f = sp.lambdify(syms, e, "numpy")
    grads = [sp.lambdify(syms, sp.diff(e, s), "numpy") for s in syms]
    def fn(x: np.ndarray) -> float:
        return float(f(*x))
    def jac(x: np.ndarray) -> np.ndarray:
        return np.array([float(g(*x)) for g in grads])
    return fn, jac


def minimize(
    expr: str,
    variables: list[str],
    x0: list[float],
    *,
    bounds: list[list[float | None]] | None = None,
    method: str = "L-BFGS-B",
) -> dict[str, Any]:
    fn, jac = _make_scalar_fn(expr, variables)
    bnds = None
    if bounds is not None:
        bnds = [(None if lo is None else float(lo), None if hi is None else float(hi)) for lo, hi in bounds]
    res = optimize.minimize(fn, np.asarray(x0, float), jac=jac, bounds=bnds, method=method)
    # Independent check: gradient norm at solution + Nelder-Mead from solution
    gnorm = float(np.linalg.norm(jac(res.x)))
    check = optimize.minimize(fn, res.x, method="Nelder-Mead", options={"maxiter": 500})
    return {
        "x": res.x.tolist(),
        "fun": float(res.fun),
        "success": bool(res.success),
        "message": str(res.message),
        "nit": int(res.nit or 0),
        "gradient_norm": gnorm,
        "independent_check_fun": float(check.fun),
        "stationary": bool(gnorm < 1e-6),
    }


def global_minimize(expr: str, variables: list[str], bounds: list[list[float]], seed: int = 0) -> dict[str, Any]:
    fn, _ = _make_scalar_fn(expr, variables)
    bnds = [(float(lo), float(hi)) for lo, hi in bounds]
    res = optimize.differential_evolution(fn, bnds, seed=seed)
    # Independent route: dual annealing with same seed family
    check = optimize.dual_annealing(fn, bnds, seed=seed + 1, maxiter=200)
    return {
        "x": res.x.tolist(),
        "fun": float(res.fun),
        "independent_fun": float(check.fun),
        "disagreement": abs(float(res.fun) - float(check.fun)),
        "nfev": int(res.nfev),
    }


def least_squares(exprs: list[str], variables: list[str], x0: list[float], data: dict[str, list[float]] | None = None) -> dict[str, Any]:
    import sympy as sp

    data = data or {}
    syms = [sp.Symbol(v) for v in variables]
    fns = [sp.lambdify(syms, sp.sympify(e), "numpy") for e in exprs]
    def residuals(x: np.ndarray) -> np.ndarray:
        return np.array([float(f(*x)) for f in fns])
    res = optimize.least_squares(residuals, np.asarray(x0, float))
    return {
        "x": res.x.tolist(),
        "cost": float(res.cost),
        "optimality": float(res.optimality),
        "success": bool(res.success),
        "residual_norm": float(np.linalg.norm(res.fun)),
    }


def sensitivity(expr: str, variables: list[str], point: list[float], rel_step: float = 1e-4) -> dict[str, Any]:
    """Normalized (logarithmic) sensitivities: d ln f / d ln x_i."""
    fn, _ = _make_scalar_fn(expr, variables)
    x = np.asarray(point, float)
    f0 = fn(x)
    sens: dict[str, float] = {}
    for i, v in enumerate(variables):
        h = rel_step * max(abs(x[i]), 1.0)
        xp, xm = x.copy(), x.copy()
        xp[i] += h
        xm[i] -= h
        dfdx = (fn(xp) - fn(xm)) / (2 * h)
        sens[v] = float(dfdx * x[i] / f0) if f0 != 0 else float("nan")
    return {"f": float(f0), "sensitivities": sens}
