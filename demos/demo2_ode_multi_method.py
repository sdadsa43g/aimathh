"""Demo 2 — Solve an ODE three independent ways and verify agreement.

  Route A: symbolic closed form (SymPy dsolve)
  Route B: numeric integration (DOP853)
  Route C: independent numeric integration (Radau) + high-precision spot check

Verdict must be VERIFIED_COMPUTATION or the demo exits non-zero.
"""

import math
import sys

import aimathh.tools  # noqa: F401
from aimathh.math import ode as O
from aimathh.verification import get_verification_engine


def main() -> None:
    print("=" * 72)
    print("DEMO 2: y' = -2y, y(0)=1 — three routes, one verdict")
    print("=" * 72)
    eng = get_verification_engine()

    # Route A: symbolic closed form.
    import sympy as sp

    t = sp.Symbol("t")
    y = sp.Function("y")
    sol = sp.dsolve(sp.Eq(y(t).diff(t), -2 * y(t)), ics={y(0): 1})
    closed = sol.rhs  # exp(-2*t)
    a_val = float(closed.subs(t, 1.0))
    print(f"\n[A] symbolic dsolve: y(t) = {closed}  ->  y(1) = {a_val:.15f}")

    # Routes B+C: two independent integrators.
    num = O.solve_ivp(["-2*y"], ["y"], [0, 1], [1.0], n_points=100)
    b_val = num["y_primary"][0][-1]
    c_val = num["y_check"][0][-1]
    print(f"[B] {num['methods']['primary']}: y(1) = {b_val:.15f}")
    print(f"[C] {num['methods']['check']}:    y(1) = {c_val:.15f}  (agree={num['agree']})")

    exact = math.exp(-2)
    vr = eng.verify_claim("y(1) = e^-2", [
        eng.numeric_agree(a_val, exact, tol=1e-12, label_a="symbolic", label_b="exact"),
        eng.numeric_agree(b_val, exact, tol=1e-8, label_a="DOP853", label_b="exact"),
        eng.numeric_agree(c_val, exact, tol=1e-6, label_a="Radau", label_b="exact"),
        eng.independent("B-vs-C", lambda: b_val, lambda: c_val),
    ], tolerance=1e-8, precision="float64 + symbolic")
    print(f"\nVerdict: {vr.status.value.upper()} / {vr.evidence_level.value.upper()}")
    for c in vr.checks:
        print(f"  [{c.status.value}] {c.detail[:130]}")
    if vr.evidence_level.value != "verified_computation":
        print("\nDEMO FAILED: expected VERIFIED_COMPUTATION")
        sys.exit(1)
    print("\nThree independent routes agree: y(1) = e^-2. VERIFIED.")


if __name__ == "__main__":
    main()
