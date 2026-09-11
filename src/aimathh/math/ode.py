"""ODE solving with built-in cross-method verification (SciPy-backed)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import integrate


def _make_rhs(exprs: list[str], vars: list[str], t_name: str = "t", params: dict[str, float] | None = None):
    import sympy as sp

    params = params or {}
    syms = {v: sp.Symbol(v) for v in vars}
    t = sp.Symbol(t_name)
    psyms = {k: sp.Symbol(k) for k in params}
    fns = []
    for e in exprs:
        parsed = sp.sympify(e, locals={**syms, t_name: t, **psyms, "sin": sp.sin, "cos": sp.cos,
                                       "exp": sp.exp, "sqrt": sp.sqrt, "pi": sp.pi, "tanh": sp.tanh})
        arg = [t] + [syms[v] for v in vars] + [psyms[k] for k in params]
        f = sp.lambdify(arg, parsed, "numpy")
        fns.append((f, list(params.values())))
    def rhs(tval: float, y: np.ndarray) -> np.ndarray:
        return np.array([f(tval, *y, *pvals) for f, pvals in fns], dtype=float)
    return rhs


def solve_ivp(
    rhs_exprs: list[str],
    variables: list[str],
    t_span: list[float],
    y0: list[float],
    *,
    params: dict[str, float] | None = None,
    method_primary: str = "DOP853",
    method_check: str = "Radau",
    rtol: float = 1e-9,
    atol: float = 1e-12,
    n_points: int = 200,
) -> dict[str, Any]:
    """Solve an IVP with two independent integrators and compare.

    Returns both trajectories plus disagreement metrics — the caller (or the
    verification engine) decides whether agreement is sufficient.
    """
    rhs = _make_rhs(rhs_exprs, variables, params=params)
    t_eval = np.linspace(t_span[0], t_span[1], n_points)
    sol1 = integrate.solve_ivp(rhs, (t_span[0], t_span[1]), np.asarray(y0, float),
                               method=method_primary, t_eval=t_eval, rtol=rtol, atol=atol)
    sol2 = integrate.solve_ivp(rhs, (t_span[0], t_span[1]), np.asarray(y0, float),
                               method=method_check, t_eval=t_eval, rtol=1e-7, atol=1e-10)
    if not sol1.success:
        raise RuntimeError(f"Primary integrator failed: {sol1.message}")
    if not sol2.success:
        raise RuntimeError(f"Check integrator failed: {sol2.message}")
    diff = np.abs(sol1.y - sol2.y)
    scale = np.maximum(1.0, np.abs(sol1.y))
    max_rel = float(np.max(diff / scale))
    return {
        "t": t_eval.tolist(),
        "y_primary": sol1.y.tolist(),
        "y_check": sol2.y.tolist(),
        "variables": variables,
        "methods": {"primary": method_primary, "check": method_check},
        "max_abs_diff": float(np.max(diff)),
        "max_rel_diff": max_rel,
        "agree": bool(max_rel < 1e-5),
        "nfev": {"primary": int(sol1.nfev), "check": int(sol2.nfev)},
    }


def solve_bvp_linear_shooting() -> dict[str, Any]:
    raise NotImplementedError("BVP solvers live behind solve_bvp; this stub is never called.")
