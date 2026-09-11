"""Demo 1 — Derive a classical-mechanics result symbolically, simulate it
numerically, and compare: the nonlinear pendulum vs its small-angle model.

Pipeline: SYMBOLIC DERIVATION -> NUMERIC SIMULATION -> VERIFICATION -> PLOT.
"""

import math

import aimathh.tools  # noqa: F401
from aimathh.math import symbolic as S
from aimathh.simulation import run_ode_simulation
from aimathh.verification import get_verification_engine
from aimathh.visualization import plots as P


def main() -> None:
    print("=" * 72)
    print("DEMO 1: pendulum — derive, simulate, compare")
    print("=" * 72)

    # 1. Symbolic derivation: linearize the pendulum EOM for small angles.
    #    theta'' + (g/L) sin(theta) = 0  ->  theta'' + (g/L) theta = 0
    print("\n[1] Symbolic: linearize sin(theta) about 0 (Taylor, order 4)")
    series = S.series_expand("sin(theta)", "theta", 0.0, 4, ["theta"])
    print("   ", series["series"])
    omega = S.simplify_expr("sqrt(g/L)", ["g", "L"])
    period = S.simplify_expr("2*pi*sqrt(L/g)", ["L", "g"])
    print("    small-angle omega =", omega["simplified"], " period =", period["latex"])

    g, L = 9.80665, 1.0
    T_small = 2 * math.pi * math.sqrt(L / g)
    print(f"    T_small-angle = {T_small:.6f} s  (L=1m)")

    # 2. Numerical simulation of the TRUE nonlinear pendulum at two amplitudes.
    print("\n[2] Numeric: simulate nonlinear pendulum at 5 deg and 60 deg")
    sims = {}
    for deg in (5, 60):
        th0 = math.radians(deg)
        # state [theta, omega]; rhs in terms of t,x.. use variables theta,w
        sim = run_ode_simulation(
            ["w", "-(g/L)*sin(theta)"], ["theta", "w"], [0, 10.0], [th0, 0.0],
            params={"g": g, "L": L},
            energy_expr="w^2/2 - (g/L)*cos(theta)")
        sims[deg] = sim
        print(f"    {deg:3d} deg: method_agreement={sim['diagnostics']['method_agreement']} "
              f"energy_conserved={sim['diagnostics']['energy']['conserved']} "
              f"(drift={sim['diagnostics']['energy']['relative_drift']:.2e})")

    # 3. Compare: measured period from zero-crossings vs small-angle prediction.
    print("\n[3] Compare measured periods against T = 2π√(L/g)")
    import numpy as np

    eng = get_verification_engine()
    for deg, sim in sims.items():
        t = np.array(sim["t"])
        w = np.array(sim["y"])[1]
        # period from successive rising zero-crossings of w after t>1
        cross = []
        for i in range(1, len(t)):
            if w[i - 1] < 0 <= w[i] and t[i] > 1.0:
                cross.append(t[i])
        T_meas = float(np.mean(np.diff(cross))) if len(cross) >= 3 else float("nan")
        err_pct = abs(T_meas - T_small) / T_small * 100
        print(f"    {deg:3d} deg: measured T = {T_meas:.6f} s  (small-angle err {err_pct:.2f}%)")
        check = eng.limiting_case(f"pendulum-{deg}deg-vs-small-angle", T_meas, T_small,
                                  tol=0.02 if deg == 5 else 0.0001)
        print(f"           L3 limiting-case check: {check.status.value} — {check.detail[:120]}")

    # 4. Plot both trajectories.
    fig = P.line_plot(
        sims[5]["t"][::4],
        {"theta (5 deg)": np.array(sims[5]["y"])[0][::4].tolist(),
         "theta (60 deg)": np.array(sims[60]["y"])[0][::4].tolist()},
        title="Nonlinear pendulum: small vs large amplitude", xtitle="t (s)", ytitle="theta (rad)")
    P.save_matplotlib_png(fig, "data/demo1_pendulum.png", "Nonlinear pendulum")
    print("\n[4] Wrote data/demo1_pendulum.png")
    print("\nConclusion: small-angle theory is VERIFIED at 5 deg (within 2%) and — correctly —")
    print("fails at 60 deg, where the full nonlinear simulation is the trusted result.")


if __name__ == "__main__":
    main()
