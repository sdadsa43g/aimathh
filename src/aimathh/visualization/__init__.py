"""Visualization specs: Plotly JSON + matplotlib PNG + 3D scene graphs."""

from aimathh.visualization.plots import (
    line_plot,
    scatter_plot,
    phase_portrait,
    vector_field_plot,
    surface_spec,
    histogram_spec,
    spectrum_plot,
    ode_trajectories_plot,
    save_matplotlib_png,
)
from aimathh.visualization.scene3d import Scene3D, surface_3d, trajectory_3d, vector_field_3d

__all__ = [
    "line_plot",
    "scatter_plot",
    "phase_portrait",
    "vector_field_plot",
    "surface_spec",
    "histogram_spec",
    "spectrum_plot",
    "ode_trajectories_plot",
    "save_matplotlib_png",
    "Scene3D",
    "surface_3d",
    "trajectory_3d",
    "vector_field_3d",
]
