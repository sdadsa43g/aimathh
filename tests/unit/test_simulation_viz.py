"""Simulators + visualization specs from real data."""

from aimathh.simulation import (
    run_heat_1d,
    run_monte_carlo_simulation,
    run_ode_simulation,
    run_parameter_sweep,
)
from aimathh.visualization import plots as P
from aimathh.visualization.scene3d import surface_3d


def test_ode_sim_energy_conservation():
    # Undamped oscillator conserves E = v^2/2 + x^2/2
    out = run_ode_simulation(["v", "-x"], ["x", "v"], [0, 6.283185307179586], [1.0, 0.0],
                             energy_expr="v^2/2+x^2/2")
    assert out["diagnostics"]["method_agreement"] is True
    assert out["diagnostics"]["energy"]["conserved"] is True
    assert out["replay"]["experiment_id"].startswith("exp_")


def test_heat_1d_matches_analytic():
    out = run_heat_1d(nx=61, nt=400, t_final=0.2)
    assert out["diagnostics"]["stable"] is True
    assert out["diagnostics"]["analytic_agrees"] is True


def test_heat_1d_rejects_unstable():
    import pytest

    with pytest.raises(ValueError, match="unstable"):
        run_heat_1d(nx=11, nt=10, t_final=10.0, alpha=1.0)


def test_sweep_monotonic_decay():
    out = run_parameter_sweep(["-k*y"], ["y"], [0, 2], [1.0], {"k": [0.5, 1.0, 2.0]})
    finals = [r["final_state"][0] for r in out["results"]]
    assert finals[0] > finals[1] > finals[2]  # faster decay -> smaller final value


def test_mc_replay_pinned():
    out = run_monte_carlo_simulation("x", ["x"], {"x": {"dist": "uniform", "low": 0, "high": 1}},
                                     n=5000, seed=7)
    assert out["replay"]["seed"] == 7
    assert abs(out["mean"] - 0.5) < 0.03


def test_line_plot_and_png(tmp_path):
    fig = P.line_plot([0, 1, 2], {"y": [0, 1, 4]}, title="parabola")
    assert fig["data"][0]["y"] == [0, 1, 4]
    path = P.save_matplotlib_png(fig, tmp_path / "p.png", "parabola")
    import os

    assert os.path.getsize(path) > 1000


def test_surface_3d_buffers():
    s = surface_3d("sin(sqrt(x^2+y^2))", n=10)
    assert len(s.objects[0]["z"]) == 10
    assert s.kind == "scene3d"
