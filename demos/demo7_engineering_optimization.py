"""Demo 7 — Engineering optimization: minimum-material cylindrical can.

  Minimize surface area S = 2πr² + 2πrh subject to V = πr²h = 1 liter.
  Analytic optimum: r = (V/2π)^(1/3), h = 2r. Numeric optimizer must agree;
  sensitivity analysis shows which dimension matters most.
"""

import math
import sys

import aimathh.tools  # noqa: F401
from aimathh.math import optimize as OPT
from aimathh.math import symbolic as S
from aimathh.verification import get_verification_engine

V = 0.001  # m^3 (1 liter)


def main() -> None:
    print("=" * 72)
    print("DEMO 7: optimize a 1-liter can for minimum material")
    print("=" * 72)

    # Analytic route: eliminate h = V/(πr²), S(r) = 2πr² + 2V/r, dS/dr = 0.
    print("\n[A] Analytic route (SymPy)")
    dS = S.differentiate("2*pi*r^2 + 2*V/r", "r", variables=["r", "V", "pi"])
    print("    dS/dr =", dS["derivative"])
    sols = S.solve_equation("4*pi*r - 2*V/r^2", "r", ["r", "V", "pi"])
    print("    stationary points:", sols["solutions"])
    r_star = (V / (2 * math.pi)) ** (1 / 3)
    h_star = V / (math.pi * r_star**2)
    S_star = 2 * math.pi * r_star**2 + 2 * math.pi * r_star * h_star
    print(f"    r* = {r_star*100:.4f} cm, h* = {h_star*100:.4f} cm (h/r = {h_star/r_star:.3f}), "
          f"S* = {S_star*1e4:.2f} cm²")

    # Numeric route: constrained minimization in (r, h) with penalty.
    print("\n[B] Numeric route (L-BFGS-B + independent global check)")
    num = OPT.minimize(
        f"(2*pi*r^2 + 2*pi*r*h) + 1e9*(pi*r^2*h - {V})^2",
        ["r", "h"], [0.02, 0.2], bounds=[[0.005, 0.2], [0.01, 0.5]])
    glo = OPT.global_minimize(
        f"(2*pi*r^2 + 2*pi*r*h) + 1e9*(pi*r^2*h - {V})^2",
        ["r", "h"], [[0.005, 0.2], [0.01, 0.5]], seed=3)
    print(f"    local:  r = {num['x'][0]*100:.4f} cm, h = {num['x'][1]*100:.4f} cm, "
          f"stationary={num['stationary']}")
    print(f"    global: r = {glo['x'][0]*100:.4f} cm, h = {glo['x'][1]*100:.4f} cm")

    eng = get_verification_engine()
    vr = eng.verify_claim("can optimum", [
        eng.numeric_agree(num["x"][0], r_star, tol=1e-3, label_a="numeric r", label_b="analytic r"),
        eng.numeric_agree(num["x"][1], h_star, tol=1e-3, label_a="numeric h", label_b="analytic h"),
        eng.limiting_case("h=2r at optimum", h_star / r_star, 2.0, tol=1e-6),
    ])
    print(f"\n    Verdict: {vr.status.value.upper()} / {vr.evidence_level.value.upper()}")

    print("\n[C] Sensitivity at optimum (normalized d ln S / d ln x)")
    sens = OPT.sensitivity("2*pi*r^2 + 2*pi*r*h", ["r", "h"], [r_star, h_star])
    print(f"    {sens['sensitivities']}  (equal shares: area splits evenly at optimum)")

    if vr.status.value != "passed":
        sys.exit(1)
    print(f"\nOptimal can: r ≈ {r_star*100:.2f} cm, h ≈ {h_star*100:.2f} cm. "
          f"{vr.evidence_level.value.upper()} by analytic + numeric routes.")


if __name__ == "__main__":
    main()
