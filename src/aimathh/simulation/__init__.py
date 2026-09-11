"""Simulation engine: ODE/PDE integration, Monte Carlo, parameter sweeps."""

from aimathh.simulation.runner import (
    run_ode_simulation,
    run_heat_1d,
    run_parameter_sweep,
    run_monte_carlo_simulation,
)

__all__ = ["run_ode_simulation", "run_heat_1d", "run_parameter_sweep", "run_monte_carlo_simulation"]
