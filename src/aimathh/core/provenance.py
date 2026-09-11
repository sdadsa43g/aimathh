"""Provenance — every tool execution records how a result was produced."""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from typing import Any

from pydantic import BaseModel, Field

from aimathh.core.ids import new_id


class Provenance(BaseModel):
    id: str = ""
    tool: str
    tool_version: str = "0.1.0"
    environment: dict[str, Any] = Field(default_factory=dict)
    input: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    source_code: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    output_digest: str = ""
    random_seed: int | None = None
    numerical_precision: str = ""
    solver_config: dict[str, Any] = Field(default_factory=dict)
    dependencies: dict[str, str] = Field(default_factory=dict)
    duration_s: float = 0.0
    success: bool = True
    error: str = ""

    def short(self) -> str:
        return f"{self.tool}@{self.timestamp.isoformat()} id={self.id}"


def _dep_versions(names: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for n in names:
        try:
            out[n] = importlib_metadata.version(n)
        except Exception:
            continue
    return out


def make_provenance(
    tool: str,
    *,
    input: dict[str, Any] | None = None,
    parameters: dict[str, Any] | None = None,
    source_code: str = "",
    seed: int | None = None,
    precision: str = "",
    solver_config: dict[str, Any] | None = None,
) -> Provenance:
    return Provenance(
        id=new_id("prov_"),
        tool=tool,
        environment={
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        input=input or {},
        parameters=parameters or {},
        source_code=source_code,
        random_seed=seed,
        numerical_precision=precision,
        solver_config=solver_config or {},
        dependencies=_dep_versions(
            ["numpy", "scipy", "sympy", "mpmath", "pint", "pandas", "jax", "jaxlib"]
        ),
    )
