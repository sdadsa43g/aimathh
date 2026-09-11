"""Unit system (Pint-backed singleton registry)."""

from __future__ import annotations

from typing import Any

import pint

_registry: pint.UnitRegistry | None = None


class UnitError(ValueError):
    pass


def get_registry() -> pint.UnitRegistry:
    global _registry
    if _registry is None:
        _registry = pint.UnitRegistry(auto_reduce_dimensions=False)
        _registry.formatter.default_format = "~P"
    return _registry


def parse_quantity(text: str) -> pint.Quantity:
    ureg = get_registry()
    try:
        q = ureg.parse_expression(text)
    except Exception as e:
        raise UnitError(f"Could not parse quantity '{text}': {e}") from e
    if not isinstance(q, pint.Quantity):
        raise UnitError(f"'{text}' is not a quantity with units")
    return q


def convert(quantity: str, to_units: str) -> dict[str, Any]:
    q = parse_quantity(quantity)
    ureg = get_registry()
    try:
        out = q.to(to_units)
    except Exception as e:
        raise UnitError(f"Cannot convert '{quantity}' to '{to_units}': {e}") from e
    return {
        "input": str(q),
        "output": str(out),
        "magnitude": float(out.magnitude),
        "units": str(out.units),
        "dimensionality": str(out.dimensionality),
    }


def dimensionality(quantity: str) -> str:
    return str(parse_quantity(quantity).dimensionality)


def to_si(quantity: str) -> dict[str, Any]:
    q = parse_quantity(quantity)
    si = q.to_base_units()
    return {"input": str(q), "si": str(si), "magnitude": float(si.magnitude), "units": str(si.units)}
