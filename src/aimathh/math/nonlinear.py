"""Nonlinear systems, fixed points, stability, phase-plane helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import optimize


def solve_nonlinear(exprs: list[str], variables: list[str], x0: list[float]) -> dict[str, Any]:
    import sympy as sp

    syms = [sp.Symbol(v) for v in variables]
    fns = [sp.lambdify(syms, sp.sympify(e), "numpy") for e in exprs]
    jac_sym = sp.Matrix(exprs and [sp.sympify(e) for e in exprs]).jacobian(syms)
    jac_fn = sp.lambdify(syms, jac_sym, "numpy")
    def f(x: np.ndarray) -> np.ndarray:
        return np.array([float(fn(*x)) for fn in fns])
    def j(x: np.ndarray) -> np.ndarray:
        return np.asarray(jac_fn(*x), dtype=float)
    sol = optimize.root(f, np.asarray(x0, float), jac=j)
    x = np.asarray(sol.x, float)
    # Independent verification: residual norm + numeric-Jacobian resolve
    res_norm = float(np.linalg.norm(f(x)))
    eig = np.linalg.eigvals(j(x))
    return {
        "x": x.tolist(),
        "success": bool(sol.success),
        "message": str(sol.message),
        "residual_norm": res_norm,
        "verified": bool(res_norm < 1e-8),
        "jacobian_eigenvalues": [{"re": float(v.real), "im": float(v.imag)} for v in eig],
    }


def fixed_point_stability(rhs_exprs: list[str], variables: list[str], point: list[float], params: dict[str, float] | None = None) -> dict[str, Any]:
    import sympy as sp

    params = params or {}
    syms = [sp.Symbol(v) for v in variables]
    psyms = {k: sp.Symbol(k) for k in params}
    vec = sp.Matrix([sp.sympify(e, locals={**{v: syms[i] for i, v in enumerate(variables)}, **psyms,
                                            "sin": sp.sin, "cos": sp.cos, "tanh": sp.tanh}) for e in rhs_exprs])
    J = vec.jacobian(syms)
    subs = {syms[i]: point[i] for i in range(len(variables))}
    subs.update({psyms[k]: v for k, v in params.items()})
    Jn = np.asarray(J.subs(subs).tolist(), dtype=float)
    eig = np.linalg.eigvals(Jn)
    res = np.asarray(vec.subs(subs).tolist(), dtype=float).ravel()
    re = [float(v.real) for v in eig]
    if max(re) < 0:
        kind = "asymptotically stable"
    elif min(re) > 0:
        kind = "unstable"
    elif any(r == 0 for r in re):
        kind = "marginal/center (linear test inconclusive)"
    else:
        kind = "saddle (unstable)"
    return {
        "jacobian": Jn.tolist(),
        "eigenvalues": [{"re": float(v.real), "im": float(v.imag)} for v in eig],
        "residual_at_point": res.tolist(),
        "is_fixed_point": bool(np.linalg.norm(res) < 1e-8),
        "stability": kind,
    }


def vector_field(rhs_exprs: list[str], variables: list[str], ranges: dict[str, list[float]], n: int = 20, params: dict[str, float] | None = None) -> dict[str, Any]:
    """Sample a 2D vector field on a grid (for phase portraits / quiver plots)."""
    import sympy as sp

    if len(variables) != 2:
        raise ValueError("vector_field currently supports exactly 2 state variables")
    params = params or {}
    syms = [sp.Symbol(v) for v in variables]
    psyms = {k: sp.Symbol(k) for k in params}
    fns = [sp.lambdify(syms, sp.sympify(e, locals={**{v: s for v, s in zip(variables, syms)}, **psyms,
                                                   "sin": sp.sin, "cos": sp.cos, "tanh": sp.tanh}), "numpy")
           for e in rhs_exprs]
    (x0, x1), (y0, y1) = ranges[variables[0]], ranges[variables[1]]
    xs = np.linspace(x0, x1, n)
    ys = np.linspace(y0, y1, n)
    X, Y = np.meshgrid(xs, ys)
    U = np.asarray(fns[0](X, Y), dtype=float)
    V = np.asarray(fns[1](X, Y), dtype=float)
    return {"x": xs.tolist(), "y": ys.tolist(), "u": U.tolist(), "v": V.tolist(), "variables": variables}
