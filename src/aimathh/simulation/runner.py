"""Concrete simulators with conservation/limit diagnostics.

Every simulator returns trajectories + diagnostics (energy drift, mass
conservation, agreement between methods) so results are checkable, and a
``replay`` block that pins seeds, tolerances and versions.
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np

from aimathh.core.ids import new_id


def _replay(seed: int | None, extra: dict[str, Any]) -> dict[str, Any]:
    from importlib import metadata as md

    deps: dict[str, str] = {}
    for pkg in ("numpy", "scipy", "sympy"):
        try:
            deps[pkg] = md.version(pkg)
        except Exception:
            pass
    return {
        "experiment_id": new_id("exp_"),
        "seed": seed,
        "python": sys.version.split()[0],
        "dependencies": deps,
        **extra,
    }


def run_ode_simulation(
    rhs_exprs: list[str],
    variables: list[str],
    t_span: list[float],
    y0: list[float],
    *,
    params: dict[str, float] | None = None,
    energy_expr: str | None = None,
    seed: int | None = None,
    n_points: int = 400,
) -> dict[str, Any]:
    from aimathh.math import ode as O

    sol = O.solve_ivp(rhs_exprs, variables, t_span, y0, params=params, n_points=n_points)
    diagnostics: dict[str, Any] = {
        "method_agreement": sol["agree"],
        "max_rel_diff": sol["max_rel_diff"],
    }
    if energy_expr is not None:
        import sympy as sp

        syms = [sp.Symbol(v) for v in variables]
        psyms = {k: sp.Symbol(k) for k in (params or {})}
        e = sp.sympify(energy_expr, locals={**{v: s for v, s in zip(variables, syms)}, **psyms,
                                            "sin": sp.sin, "cos": sp.cos, "sqrt": sp.sqrt})
        f = sp.lambdify(syms + [psyms[k] for k in (params or {})], e, "numpy")
        y = np.array(sol["y_primary"])
        pvals = [params[k] for k in (params or {})]
        energies = np.array([float(f(*[y[i, j] for i in range(len(variables))], *pvals)) for j in range(y.shape[1])])
        drift = float(np.max(np.abs(energies - energies[0])) / max(1.0, abs(energies[0])))
        diagnostics["energy"] = {"initial": float(energies[0]), "final": float(energies[-1]), "relative_drift": drift,
                                 "conserved": bool(drift < 1e-4)}
    return {
        "kind": "ode",
        "t": sol["t"],
        "y": sol["y_primary"],
        "variables": variables,
        "methods": sol["methods"],
        "diagnostics": diagnostics,
        "replay": _replay(seed, {"t_span": t_span, "y0": y0, "params": params or {}}),
    }


def run_heat_1d(
    *,
    L: float = 1.0,
    nx: int = 101,
    alpha: float = 0.01,
    t_final: float = 0.5,
    nt: int = 200,
    left: float = 0.0,
    right: float = 0.0,
    initial: str = "sin(pi*x/L)",
    seed: int | None = None,
) -> dict[str, Any]:
    """1-D heat equation u_t = alpha u_xx, explicit FTCS + analytic cross-check.

    For sinusoidal initial data the analytic solution is exact, giving a true
    independent check of the PDE solver (not just self-convergence).
    """
    import sympy as sp

    x = np.linspace(0, L, nx)
    dx = x[1] - x[0]
    dt = t_final / nt
    r = alpha * dt / dx**2
    if r > 0.5:
        raise ValueError(f"Explicit scheme unstable: r={r:.3f} > 0.5. Reduce dt or increase nx.")
    X, LL = sp.Symbol("x"), sp.Symbol("L")
    init_sym = sp.sympify(initial, locals={"x": X, "L": LL, "pi": sp.pi, "sin": sp.sin,
                                           "cos": sp.cos, "exp": sp.exp}).subs(LL, L)
    init = sp.lambdify(X, init_sym, "numpy")
    u = np.asarray(init(x), dtype=float)
    # Analytic solution for u(x,0)=sin(pi x/L): u = sin(pi x/L) exp(-alpha (pi/L)^2 t)
    analytic_ok = initial.replace(" ", "") in ("sin(pi*x/L)", "sin(pi*x/L)")
    snapshots = [u.copy()]
    for _ in range(nt):
        u_new = u.copy()
        u_new[1:-1] = u[1:-1] + r * (u[2:] - 2 * u[1:-1] + u[:-2])
        u_new[0], u_new[-1] = left, right
        u = u_new
        if len(snapshots) < 6:
            snapshots.append(u.copy())
    snapshots.append(u.copy())
    diagnostics: dict[str, Any] = {"cfl_r": r, "stable": bool(r <= 0.5)}
    if analytic_ok:
        exact = np.sin(np.pi * x / L) * np.exp(-alpha * (np.pi / L) ** 2 * t_final)
        err = float(np.max(np.abs(u - exact)))
        diagnostics["analytic_max_error"] = err
        diagnostics["analytic_agrees"] = bool(err < 5e-3)
    return {
        "kind": "heat_1d",
        "x": x.tolist(),
        "final": u.tolist(),
        "snapshots": [s.tolist() for s in snapshots],
        "params": {"L": L, "nx": nx, "alpha": alpha, "t_final": t_final, "nt": nt},
        "diagnostics": diagnostics,
        "replay": _replay(seed, {"scheme": "FTCS", "r": r}),
    }


def run_parameter_sweep(
    rhs_exprs: list[str],
    variables: list[str],
    t_span: list[float],
    y0: list[float],
    sweep: dict[str, list[float]],
    *,
    params: dict[str, float] | None = None,
    observable: str | None = None,
) -> dict[str, Any]:
    """1-D parameter sweep: vary one param, record final state / observable."""
    from aimathh.math import ode as O

    if len(sweep) != 1:
        raise ValueError("sweep must contain exactly one parameter")
    pname, values = next(iter(sweep.items()))
    base = dict(params or {})
    results: list[dict[str, Any]] = []
    obs_fn = None
    if observable is not None:
        import sympy as sp

        syms = [sp.Symbol(v) for v in variables]
        psyms = {k: sp.Symbol(k) for k in {**base, pname: 0.0}}
        obs_fn = sp.lambdify(syms + [psyms[k] for k in {**base, pname: 0.0}],
                             sp.sympify(observable), "numpy")
    for v in values:
        p = {**base, pname: float(v)}
        sol = O.solve_ivp(rhs_exprs, variables, t_span, y0, params=p, n_points=100)
        yf = [float(sol["y_primary"][i][-1]) for i in range(len(variables))]
        entry: dict[str, Any] = {"param": float(v), "final_state": yf, "agree": sol["agree"]}
        if obs_fn is not None:
            entry["observable"] = float(obs_fn(*yf, *[p[k] for k in {**base, pname: 0.0}]))
        results.append(entry)
    return {"kind": "parameter_sweep", "parameter": pname, "values": values, "results": results,
            "replay": _replay(None, {"t_span": t_span, "y0": y0})}


def run_monte_carlo_simulation(
    expr: str, variables: list[str], distributions: dict[str, dict[str, Any]],
    n: int = 50_000, seed: int = 0,
) -> dict[str, Any]:
    from aimathh.math import stats as S

    out = S.monte_carlo(expr, variables, distributions, n=n, seed=seed)
    out["replay"] = _replay(seed, {"expr": expr, "n": n})
    out["kind"] = "monte_carlo"
    return out
