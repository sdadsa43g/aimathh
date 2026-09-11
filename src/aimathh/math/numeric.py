"""Arbitrary-precision numerical evaluation (mpmath-backed)."""

from __future__ import annotations

from typing import Any

import mpmath as mp


def evaluate(expr: str, variables: dict[str, float | str] | None = None, dps: int = 15) -> dict[str, Any]:
    """Evaluate an expression string at arbitrary precision.

    ``variables`` maps names to numbers (or numeric strings). Returns the
    value at ``dps`` decimal places plus a higher-precision cross-check.
    """
    variables = variables or {}
    with mp.workdps(dps):
        env = {k: mp.mpf(str(v)) for k, v in variables.items()}
        env.update({k: getattr(mp, k) for k in ("pi", "e", "euler", "inf", "nan") if hasattr(mp, k)})
        for fn in ("sin", "cos", "tan", "exp", "log", "sqrt", "sinh", "cosh", "tanh", "gamma", "erf", "factorial"):
            env[fn] = getattr(mp, fn)
        try:
            val = mp.mpf(eval(expr, {"__builtins__": {}}, env))  # noqa: S307 (sandboxed numeric eval)
        except Exception as e:
            # Fall back to sympy parsing for richer syntax, then mpmath eval
            import sympy as sp

            e2 = sp.sympify(expr)
            subs = {sp.Symbol(k): float(v) for k, v in variables.items()}
            val = mp.mpf(e2.subs(subs).evalf(dps))
            _ = e
        main = mp.nstr(val, dps)
    with mp.workdps(dps + 15):
        try:
            env2 = {k: mp.mpf(str(v)) for k, v in variables.items()}
            for fn in ("sin", "cos", "tan", "exp", "log", "sqrt", "sinh", "cosh", "tanh", "gamma", "erf", "factorial"):
                env2[fn] = getattr(mp, fn)
            env2.update({"pi": mp.pi, "e": mp.e})
            check = mp.mpf(eval(expr, {"__builtins__": {}}, env2))  # noqa: S307
        except Exception:
            import sympy as sp

            e2 = sp.sympify(expr)
            subs = {sp.Symbol(k): float(v) for k, v in variables.items()}
            check = mp.mpf(e2.subs(subs).evalf(dps + 15))
    # Compare inside a high-precision context: converting the dps-digit value
    # at default (15-digit) precision would destroy the comparison.
    with mp.workdps(dps + 15):
        v_main = mp.mpf(main)
        v_check = mp.mpf(check)
        if v_check != 0:
            rel_diff = abs((v_check - v_main) / v_check)
        else:
            rel_diff = abs(v_check - v_main)
        stable = bool(rel_diff < mp.mpf(10) ** (-(dps - 3)))
        cross_str = mp.nstr(v_check, dps + 5)
    return {
        "expression": expr,
        "dps": dps,
        "value": main,
        "cross_check_dps": dps + 15,
        "cross_check_value": cross_str,
        "relative_disagreement": float(rel_diff),
        "stable": stable,
    }


def constants(dps: int = 50) -> dict[str, str]:
    with mp.workdps(dps):
        return {
            "pi": mp.nstr(mp.pi, dps),
            "e": mp.nstr(mp.e, dps),
            "euler_gamma": mp.nstr(mp.euler, dps),
            "sqrt2": mp.nstr(mp.sqrt(2), dps),
            "golden_ratio": mp.nstr((1 + mp.sqrt(5)) / 2, dps),
        }


def quad_high_precision(
    expr: str, var: str, a: float, b: float, dps: int = 30
) -> dict[str, Any]:
    """Adaptive quadrature at arbitrary precision (independent route vs SciPy)."""
    import sympy as sp

    e = sp.sympify(expr)
    s = sp.Symbol(var)
    f = sp.lambdify(s, e, "mpmath")
    with mp.workdps(dps):
        val = mp.quad(f, [a, b])
        val2 = mp.quad(f, [a, b], maxdegree=12)
        denom = abs(val) if val != 0 else mp.mpf(1)
        rel = abs((val - val2) / denom)
    return {
        "expression": expr,
        "interval": [a, b],
        "dps": dps,
        "value": mp.nstr(val, dps),
        "independent_value": mp.nstr(val2, dps),
        "relative_disagreement": float(rel),
        "stable": bool(rel < mp.mpf(10) ** (-(dps - 5))),
    }
