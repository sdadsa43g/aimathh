"""Dimensional analysis: parse equations, verify homogeneity of dimensions.

The model supplies candidate equations as strings plus a symbol->units table.
The checker substitutes dimensions and requires every additive term to match.
This catches an entire class of hallucinated physics before presentation.
"""

from __future__ import annotations

import numbers
from typing import Any

import pint
import sympy as sp
from pydantic import BaseModel, Field

from aimathh.physics.units import UnitError, get_registry


def _top_level_terms(expr: sp.Expr) -> list[sp.Expr]:
    if isinstance(expr, sp.Add):
        return list(expr.args)
    return [expr]


class DimensionalReport(BaseModel):
    equation: str
    consistent: bool
    lhs_dimensionality: str = ""
    rhs_dimensionality: str = ""
    term_dimensionalities: list[str] = Field(default_factory=list)
    mismatches: list[str] = Field(default_factory=list)
    detail: str = ""


def _build_env(symbol_units: dict[str, str], ureg: pint.UnitRegistry) -> dict[str, pint.Quantity]:
    env: dict[str, pint.Quantity] = {}
    for name, units in symbol_units.items():
        try:
            env[name] = ureg.Quantity(1.0, units)
        except Exception as e:
            raise UnitError(f"Bad units for '{name}': '{units}' ({e})") from e
    return env


def _dim(q: pint.Quantity, ureg: pint.UnitRegistry) -> pint.Quantity:
    """Keep only the dimension: reset magnitude to 1 to avoid arithmetic
    artifacts (e.g. 1-1=0 raised to a negative power)."""
    return ureg.Quantity(1.0, q.units)


def _eval(node: Any, env: dict[str, pint.Quantity], ureg: pint.UnitRegistry) -> pint.Quantity:
    """Recursively evaluate the *dimensions* of a SymPy node.

    Never substitutes Quantity objects into SymPy (SymPy would call float()
    on them); instead walks the tree with an explicit environment.
    Magnitudes are normalized to 1 at every step — only dimensions matter.
    """
    if isinstance(node, pint.Quantity):
        return _dim(node, ureg)
    if isinstance(node, sp.Symbol):
        name = str(node)
        if name not in env:
            raise UnitError(
                f"No units given for symbol '{name}'. Provide units for every symbol "
                "(use 'dimensionless' for pure numbers)."
            )
        return env[name]
    if isinstance(node, (sp.Number, numbers.Number)):
        return ureg.Quantity(float(node), "dimensionless")
    if isinstance(node, sp.Add):
        total: pint.Quantity | None = None
        for a in node.args:
            q = _eval(a, env, ureg)
            total = q if total is None else total + q  # raises DimensionalityError on mismatch
        assert total is not None
        return _dim(total, ureg)
    if isinstance(node, sp.Mul):
        prod = ureg.Quantity(1.0, "dimensionless")
        for a in node.args:
            prod = _dim(prod * _eval(a, env, ureg), ureg)
        return prod
    if isinstance(node, sp.Pow):
        base = _eval(node.args[0], env, ureg)
        exp = node.args[1]
        if not exp.is_number:
            raise UnitError(f"Non-numeric exponent {exp} is not dimensionally analyzable")
        return _dim(base ** float(exp), ureg)
    if isinstance(node, sp.Function):
        fname = type(node).__name__
        args = [_eval(a, env, ureg) for a in node.args]
        if fname in ("sin", "cos", "tan", "exp", "log", "ln", "sinh", "cosh", "tanh",
                     "asin", "acos", "atan", "erf", "gamma"):
            for a in args:
                if not a.dimensionless:
                    raise UnitError(
                        f"{fname}(...) argument must be dimensionless, got {a.dimensionality}")
            return ureg.Quantity(1.0, "dimensionless")
        if fname == "sqrt":
            return args[0] ** 0.5
        if fname == "Abs":
            return args[0]
        raise UnitError(f"Unsupported function in dimensional analysis: {fname}")
    if isinstance(node, sp.Equality):
        lq, rq = _eval(node.lhs, env, ureg), _eval(node.rhs, env, ureg)
        if lq.dimensionality != rq.dimensionality:
            raise pint.DimensionalityError(lq.units, rq.units)
        return lq
    try:
        return ureg.Quantity(float(node), "dimensionless")
    except Exception as e:
        raise UnitError(f"Cannot analyze node {node!r}: {e}") from e


def check_equation(equation: str, symbol_units: dict[str, str]) -> DimensionalReport:
    """Check ``lhs = rhs`` (or a bare expression, checked for internal consistency)."""
    if "=" in equation:
        lhs_s, rhs_s = equation.split("=", 1)
    else:
        lhs_s, rhs_s = equation, equation
    # Force every declared symbol to parse as a Symbol so that names like E
    # (Euler's number in SymPy) are treated as the user's physical quantity.
    locals_map: dict[str, Any] = {name: sp.Symbol(name) for name in symbol_units}
    try:
        lhs = sp.sympify(lhs_s, locals=locals_map)
        rhs = sp.sympify(rhs_s, locals=locals_map)
    except Exception as e:
        return DimensionalReport(equation=equation, consistent=False,
                                 detail=f"Parse error: {e}", mismatches=[f"parse: {e}"])
    ureg = get_registry()
    try:
        env = _build_env(symbol_units, ureg)
    except UnitError as e:
        return DimensionalReport(equation=equation, consistent=False,
                                 detail=str(e), mismatches=[str(e)])
    mismatches: list[str] = []
    term_dims: list[str] = []
    for label, expr in (("LHS", lhs), ("RHS", rhs)):
        for term in _top_level_terms(expr):
            try:
                q = _eval(term, env, ureg)
                term_dims.append(f"{label} term {term}: {q.dimensionality}")
            except Exception as e:  # noqa: BLE001
                mismatches.append(f"{label} term {term}: {e}")
    lhs_dim = rhs_dim = ""
    if not mismatches:
        try:
            lq = _eval(lhs, env, ureg)
            rq = _eval(rhs, env, ureg)
            lhs_dim, rhs_dim = str(lq.dimensionality), str(rq.dimensionality)
            if lq.dimensionality != rq.dimensionality:
                mismatches.append(
                    f"LHS dimensionality {lq.dimensionality} != RHS {rq.dimensionality}")
        except Exception as e:  # noqa: BLE001
            mismatches.append(str(e))
    consistent = not mismatches
    detail = "Dimensionally consistent." if consistent else "DIMENSIONAL MISMATCH: " + "; ".join(mismatches)
    return DimensionalReport(
        equation=equation,
        consistent=consistent,
        lhs_dimensionality=lhs_dim,
        rhs_dimensionality=rhs_dim,
        term_dimensionalities=term_dims,
        mismatches=mismatches,
        detail=detail,
    )
