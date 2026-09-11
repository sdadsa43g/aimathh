"""Symbolic mathematics engine (SymPy-backed, dependency-injected).

All functions accept strings or SymPy objects and return structured dicts so
tool outputs are JSON-serializable. Precision of *claims* matters: every
operation reports exactly what was computed.
"""

from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import Matrix
from sympy.utilities.lambdify import lambdastr


def parse_expr(expr: str, variables: list[str] | None = None) -> sp.Expr:
    """Parse a string into a SymPy expression with explicit symbols."""
    syms = {v: sp.Symbol(v) for v in (variables or [])}
    # Discover bare symbols automatically as well.
    parsed = sp.sympify(expr, locals={**_COMMON, **syms})
    return parsed  # type: ignore[no-any-return]


_COMMON: dict[str, Any] = {
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "exp": sp.exp,
    "log": sp.log,
    "ln": sp.log,
    "sqrt": sp.sqrt,
    "pi": sp.pi,
    "E": sp.E,
    "oo": sp.oo,
    "I": sp.I,
    "Abs": sp.Abs,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "erf": sp.erf,
    "gamma": sp.gamma,
    "Matrix": Matrix,
}


def simplify_expr(expr: str, variables: list[str] | None = None) -> dict[str, Any]:
    e = parse_expr(expr, variables)
    s = sp.simplify(e)
    return {"input": str(e), "simplified": str(s), "latex": sp.latex(s)}


def expand_expr(expr: str, variables: list[str] | None = None) -> dict[str, Any]:
    e = parse_expr(expr, variables)
    s = sp.expand(e)
    return {"input": str(e), "expanded": str(s), "latex": sp.latex(s)}


def factor_expr(expr: str, variables: list[str] | None = None) -> dict[str, Any]:
    e = parse_expr(expr, variables)
    s = sp.factor(e)
    return {"input": str(e), "factored": str(s), "latex": sp.latex(s)}


def differentiate(expr: str, var: str, order: int = 1, variables: list[str] | None = None) -> dict[str, Any]:
    e = parse_expr(expr, variables)
    s = sp.diff(e, sp.Symbol(var), order)
    return {"input": str(e), "variable": var, "order": order, "derivative": str(s), "latex": sp.latex(s)}


def integrate(expr: str, var: str, a: str | None = None, b: str | None = None, variables: list[str] | None = None) -> dict[str, Any]:
    e = parse_expr(expr, variables)
    x = sp.Symbol(var)
    if a is not None and b is not None:
        s = sp.integrate(e, (x, parse_expr(a), parse_expr(b)))
        kind = "definite"
    else:
        s = sp.integrate(e, x)
        kind = "indefinite"
    unevaluated = isinstance(s, sp.Integral)
    return {
        "input": str(e),
        "kind": kind,
        "result": str(s),
        "latex": sp.latex(s),
        "unevaluated": unevaluated,
        "warning": "Integral could not be evaluated in closed form" if unevaluated else "",
    }


def solve_equation(equation: str, var: str, variables: list[str] | None = None) -> dict[str, Any]:
    """Solve ``equation == 0`` (or 'lhs = rhs') for var."""
    if "=" in equation:
        lhs_s, rhs_s = equation.split("=", 1)
        eq = parse_expr(lhs_s, variables) - parse_expr(rhs_s, variables)
    else:
        eq = parse_expr(equation, variables)
    sols = sp.solve(eq, sp.Symbol(var), dict=False)
    return {"equation": str(eq) + " = 0", "variable": var, "solutions": [str(s) for s in sols]}


def solve_system(equations: list[str], variables: list[str]) -> dict[str, Any]:
    eqs = []
    for e in equations:
        if "=" in e:
            l, r = e.split("=", 1)
            eqs.append(parse_expr(l, variables) - parse_expr(r, variables))
        else:
            eqs.append(parse_expr(e, variables))
    syms = [sp.Symbol(v) for v in variables]
    sols = sp.solve(eqs, syms, dict=True)
    return {
        "equations": [str(e) + " = 0" for e in eqs],
        "variables": variables,
        "solutions": [{str(k): str(v) for k, v in s.items()} for s in sols],
    }


def series_expand(expr: str, var: str, point: float = 0.0, order: int = 6, variables: list[str] | None = None) -> dict[str, Any]:
    e = parse_expr(expr, variables)
    s = sp.series(e, sp.Symbol(var), point, order)
    return {"input": str(e), "series": str(s), "latex": sp.latex(s), "order": order}


def limit_expr(expr: str, var: str, point: str, direction: str = "+-", variables: list[str] | None = None) -> dict[str, Any]:
    e = parse_expr(expr, variables)
    p = parse_expr(point)
    if direction in ("+", "-"):
        s = sp.limit(e, sp.Symbol(var), p, direction)
    else:
        s = sp.limit(e, sp.Symbol(var), p)
    return {"input": str(e), "limit": str(s), "latex": sp.latex(s)}


def matrix_op(op: str, matrices: list[list[list[float]]]) -> dict[str, Any]:
    """Exact/symbolic matrix ops: det, inv, eigenvals, eigenvects, rank, lu, qr."""
    mats = [Matrix(m) for m in matrices]
    a = mats[0]
    if op == "det":
        r = a.det()
        return {"op": op, "result": str(r), "latex": sp.latex(r)}
    if op == "inv":
        r = a.inv()
        return {"op": op, "result": str(r.tolist()), "latex": sp.latex(r)}
    if op == "eigenvals":
        r = a.eigenvals()
        return {"op": op, "result": {str(k): v for k, v in r.items()}}
    if op == "eigenvects":
        vecs = []
        for val, mult, basis in a.eigenvects():
            vecs.append({"value": str(val), "multiplicity": mult, "vectors": [str(v.T.tolist()) for v in basis]})
        return {"op": op, "result": vecs}
    if op == "rank":
        return {"op": op, "result": int(a.rank())}
    if op == "multiply":
        r = mats[0]
        for m in mats[1:]:
            r = r * m
        return {"op": op, "result": str(r.tolist()), "latex": sp.latex(r)}
    raise ValueError(f"Unknown symbolic matrix op '{op}'")


def to_numeric_function(expr: str, variables: list[str], backend: str = "numpy") -> str:
    """Return Python source for a numeric evaluator (for independent recomputation)."""
    e = parse_expr(expr, variables)
    syms = [sp.Symbol(v) for v in variables]
    src = lambdastr(syms, e, printer="numpy" if backend == "numpy" else "math")
    return src


def are_symbolically_equal(a: str, b: str, variables: list[str] | None = None) -> dict[str, Any]:
    """Structural equality check via simplification of the difference."""
    ea, eb = parse_expr(a, variables), parse_expr(b, variables)
    diff = sp.simplify(ea - eb)
    equal = diff == 0
    # Fallback: trig-aware + nsimplify
    method = "simplify(diff)==0"
    if not equal:
        diff2 = sp.trigsimp(ea - eb)
        if diff2 == 0:
            equal, diff, method = True, diff2, "trigsimp(diff)==0"
    return {"a": str(ea), "b": str(eb), "equal": bool(equal), "difference": str(diff), "method": method}
