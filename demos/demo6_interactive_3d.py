"""Demo 6 — Interactive 3D scientific visualization from computed data.

Builds a 3D scene-graph (wave-interference surface + Lorenz trajectory) and a
standalone interactive HTML artifact (Plotly). All buffers are computed, not
described.
"""

from pathlib import Path

import numpy as np

from aimathh.artifacts import get_artifact_store
from aimathh.simulation import run_ode_simulation
from aimathh.visualization.scene3d import Scene3D, surface_3d, trajectory_3d


def main() -> None:
    print("=" * 72)
    print("DEMO 6: interactive 3D visualization")
    print("=" * 72)
    store = get_artifact_store()

    # Scene 1: interference surface z = sin(r)/r-like ripple, computed on a grid.
    scene = surface_3d("sin(sqrt(x^2+y^2))/ (0.2+sqrt(x^2+y^2)/4)", n=80,
                       title="Ripple: sin(r)/(0.2+r/4)")
    print(f"\n[1] surface scene: {len(scene.objects[0]['z'])}x{len(scene.objects[0]['z'][0])} grid, "
          f"title='{scene.title}'")

    # Scene 2: Lorenz attractor trajectory from a real ODE integration.
    sim = run_ode_simulation(
        ["sigma*(y-x)", "x*(rho-z)-y", "x*y-beta*z"], ["x", "y", "z"],
        [0, 25.0], [1.0, 1.0, 1.0],
        params={"sigma": 10.0, "rho": 28.0, "beta": 8 / 3},)
    y = np.array(sim["y"])
    pts = [[float(y[0, i]), float(y[1, i]), float(y[2, i])] for i in range(0, y.shape[1], 2)]
    traj = trajectory_3d(pts, title="Lorenz attractor (sigma=10, rho=28, beta=8/3)")
    print(f"[2] Lorenz trajectory: {len(pts)} points, integrators agree={sim['diagnostics']['method_agreement']}")
    print("    (pointwise disagreement is EXPECTED for chaos: trajectories diverge as e^(λt);")
    print("     the verified object here is the attractor geometry, not a single trajectory.)")

    combined = Scene3D(title="Demo 6 scenes", objects=[scene.objects[0], traj.objects[0]])
    art = store.save_json(combined.model_dump(), "demo6_scene.json", kind="scene3d",
                          description="Ripple surface + Lorenz trajectory scene graph")
    print(f"[3] scene-graph artifact: {art.id} ({art.size_bytes} bytes, sha256={art.sha256[:12]}...)")

    # Standalone interactive HTML (Plotly) anyone can open in a browser.
    import plotly.graph_objects as go

    z = np.array(scene.objects[0]["z"])
    fig = go.Figure(data=[go.Surface(z=z, colorscale="Viridis"),
                          go.Scatter3d(x=[p[0] for p in pts], y=[p[1] for p in pts], z=[p[2] for p in pts],
                                       mode="lines", line={"width": 2, "color": "red"}, name="Lorenz")])
    fig.update_layout(title="Demo 6 — computed 3D: ripple surface + Lorenz attractor")
    html_path = Path("data/demo6_interactive_3d.html")
    html_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(html_path))
    store.save_file(html_path, kind="report", description="Interactive 3D HTML (Plotly)")
    print(f"[4] wrote {html_path} ({html_path.stat().st_size // 1024} KB) — open in a browser to explore.")


if __name__ == "__main__":
    main()
