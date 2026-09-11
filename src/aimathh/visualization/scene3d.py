"""3D scene-graph specs rendered by the frontend (Three.js).

The backend emits JSON scenes; it never screenshots its own claims. Scenes
reference computed buffers so the UI can rotate/zoom without recomputation.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from pydantic import BaseModel, Field


class Scene3D(BaseModel):
    kind: str = "scene3d"
    title: str = ""
    objects: list[dict[str, Any]] = Field(default_factory=list)
    camera: dict[str, Any] = Field(default_factory=lambda: {"position": [3, 3, 3], "target": [0, 0, 0]})
    meta: dict[str, Any] = Field(default_factory=dict)

    def add(self, obj: dict[str, Any]) -> "Scene3D":
        self.objects.append(obj)
        return self


def surface_3d(
    expr: str,
    x_range: list[float] = (-3, 3),
    y_range: list[float] = (-3, 3),
    n: int = 60,
    title: str = "",
) -> Scene3D:
    import sympy as sp

    x, y = sp.Symbol("x"), sp.Symbol("y")
    e = sp.sympify(expr, locals={"x": x, "y": y, "sin": sp.sin, "cos": sp.cos, "exp": sp.exp,
                                 "sqrt": sp.sqrt, "pi": sp.pi})
    f = sp.lambdify((x, y), e, "numpy")
    xs = np.linspace(*x_range, n)
    ys = np.linspace(*y_range, n)
    X, Y = np.meshgrid(xs, ys)
    Z = np.asarray(f(X, Y), dtype=float)
    Z = np.where(np.isfinite(Z), Z, 0.0)
    scene = Scene3D(title=title or f"z = {expr}")
    scene.add({"type": "surface", "x": xs.tolist(), "y": ys.tolist(), "z": Z.tolist(),
               "colormap": "viridis", "expr": expr})
    return scene


def trajectory_3d(points: list[list[float]], title: str = "Trajectory", color: str = "#ff5533") -> Scene3D:
    scene = Scene3D(title=title)
    scene.add({"type": "line3", "points": points, "color": color})
    return scene


def vector_field_3d(
    exprs: list[str],
    ranges: dict[str, list[float]],
    n: int = 8,
    title: str = "Vector field 3D",
) -> Scene3D:
    import sympy as sp

    vars3 = ["x", "y", "z"]
    syms = [sp.Symbol(v) for v in vars3]
    fns = [sp.lambdify(syms, sp.sympify(e), "numpy") for e in exprs]
    axes = [np.linspace(*ranges[v], n) for v in vars3]
    X, Y, Z = np.meshgrid(*axes, indexing="ij")
    U = np.asarray(fns[0](X, Y, Z), dtype=float)
    V = np.asarray(fns[1](X, Y, Z), dtype=float)
    W = np.asarray(fns[2](X, Y, Z), dtype=float)
    origins, dirs = [], []
    for i in range(n):
        for j in range(n):
            for k in range(n):
                origins.append([float(X[i, j, k]), float(Y[i, j, k]), float(Z[i, j, k])])
                dirs.append([float(U[i, j, k]), float(V[i, j, k]), float(W[i, j, k])])
    scene = Scene3D(title=title)
    scene.add({"type": "arrows3", "origins": origins, "directions": dirs})
    return scene
