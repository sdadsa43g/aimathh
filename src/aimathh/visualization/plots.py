"""Declarative Plotly figure builders + headless PNG rendering.

The AI produces *specs computed from actual data*; the frontend renders them.
Every builder takes numeric data (not prose) so fabricated plots are
structurally impossible — no data, no figure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def _fig(data: list[dict], layout: dict | None = None) -> dict[str, Any]:
    return {"data": data, "layout": layout or {}}


def line_plot(x: list[float], ys: dict[str, list[float]], title: str = "", xtitle: str = "x", ytitle: str = "y") -> dict[str, Any]:
    return _fig(
        [{"type": "scatter", "mode": "lines", "x": x, "y": y, "name": name} for name, y in ys.items()],
        {"title": {"text": title}, "xaxis": {"title": xtitle}, "yaxis": {"title": ytitle}},
    )


def scatter_plot(x: list[float], y: list[float], title: str = "", name: str = "data") -> dict[str, Any]:
    return _fig([{"type": "scatter", "mode": "markers", "x": x, "y": y, "name": name}], {"title": {"text": title}})


def ode_trajectories_plot(t: list[float], y: list[list[float]], variables: list[str], title: str = "ODE solution") -> dict[str, Any]:
    return line_plot(t, {v: y[i] for i, v in enumerate(variables)}, title=title, xtitle="t")


def phase_portrait(x: list[float], y: list[float], xlabel: str = "x", ylabel: str = "y", title: str = "Phase portrait") -> dict[str, Any]:
    return _fig(
        [{"type": "scatter", "mode": "lines", "x": x, "y": y, "name": "trajectory",
          "line": {"color": "royalblue"}}],
        {"title": {"text": title}, "xaxis": {"title": xlabel}, "yaxis": {"title": ylabel},
         "aspectmode": "cube" if False else "auto"},
    )


def vector_field_plot(field: dict[str, Any], title: str = "Vector field") -> dict[str, Any]:
    # Plotly cone/quiver via scatter + line segments (dependency-free on frontend extras)
    xs = np.asarray(field["x"])
    ys = np.asarray(field["y"])
    U = np.asarray(field["u"])
    V = np.asarray(field["v"])
    X, Y = np.meshgrid(xs, ys)
    scale = max(float(np.max(np.abs(U))), float(np.max(np.abs(V))), 1e-12)
    dx = (xs[-1] - xs[0]) / len(xs) * 0.9
    segs_x: list[float | None] = []
    segs_y: list[float | None] = []
    for i in range(len(ys)):
        for j in range(len(xs)):
            x0, y0 = float(X[i, j]), float(Y[i, j])
            x1 = x0 + float(U[i, j]) / scale * dx
            y1 = y0 + float(V[i, j]) / scale * dx
            segs_x += [x0, x1, None]
            segs_y += [y0, y1, None]
    return _fig(
        [{"type": "scatter", "mode": "lines", "x": segs_x, "y": segs_y, "name": "field",
          "line": {"color": "teal", "width": 1}}],
        {"title": {"text": title}, "xaxis": {"title": field["variables"][0]},
         "yaxis": {"title": field["variables"][1]}},
    )


def surface_spec(x: list[float], y: list[float], z: list[list[float]], title: str = "Surface") -> dict[str, Any]:
    return _fig(
        [{"type": "surface", "x": x, "y": y, "z": z, "colorscale": "Viridis"}],
        {"title": {"text": title}, "scene": {"xaxis": {"title": "x"}, "yaxis": {"title": "y"},
                                             "zaxis": {"title": "z"}}},
    )


def histogram_spec(values: list[float], title: str = "Histogram", nbins: int = 50) -> dict[str, Any]:
    return _fig(
        [{"type": "histogram", "x": values, "nbinsx": nbins, "name": "samples"}],
        {"title": {"text": title}},
    )


def spectrum_plot(freqs: list[float], mags: list[float], title: str = "Spectrum") -> dict[str, Any]:
    return line_plot(freqs, {"|X(f)|": mags}, title=title, xtitle="frequency", ytitle="magnitude")


def save_matplotlib_png(fig_spec: dict[str, Any], path: str | Path, title: str = "") -> str:
    """Headless PNG fallback for reports/artifacts (matplotlib Agg)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    for trace in fig_spec.get("data", []):
        t = trace.get("type", "scatter")
        if t == "histogram":
            ax.hist(trace.get("x", []), bins=trace.get("nbinsx", 50), alpha=0.7, label=trace.get("name", ""))
        elif trace.get("mode") == "markers":
            ax.scatter(trace.get("x", []), trace.get("y", []), s=8, label=trace.get("name", ""))
        else:
            x, y = trace.get("x", []), trace.get("y", [])
            # strip None separators
            if any(v is None for v in (x or [])):
                x = [v for v in x if v is not None]
                y = [v for v in y if v is not None]
            ax.plot(x or [], y or [], label=trace.get("name", ""))
    ax.set_title(title or fig_spec.get("layout", {}).get("title", {}).get("text", ""))
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return str(path)
