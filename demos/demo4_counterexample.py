"""Demo 4 — Attack mathematical conjectures computationally.

  Conjecture 1 (FALSE): x^3 - 2x + 1 >= 0 for x in [-2, 2]  -> must be REFUTED
  Conjecture 2 (TRUE):  x^2 + 1 >= 1 for x in [-5, 5]        -> no counterexample

Exits non-zero if the false claim survives or the true claim is "refuted".
"""

import sys

from aimathh.verification import get_counterexample_engine


def main() -> None:
    print("=" * 72)
    print("DEMO 4: counterexample engine vs two conjectures")
    print("=" * 72)
    eng = get_counterexample_engine()
    fails = 0

    print("\n[C1] Claim: x^3 - 2x + 1 >= 0 on [-2, 2]")
    r1 = eng.attack("x^3-2*x+1", ["x"], {"x": [-2, 2]}, n_random=5000)
    print(f"     status: {r1['status']} via {r1.get('found_via', r1.get('attempts'))}")
    if r1["status"] == "refuted":
        x = r1["counterexample"]["x"]
        print(f"     counterexample: x = {x:.6f}, f(x) = {r1['predicate_value']:.6f} < 0  -> REFUTED")
    else:
        print("     MISSED a real counterexample!")
        fails += 1

    print("\n[C2] Claim: x^2 + 1 >= 1 on [-5, 5]")
    r2 = eng.attack("x^2+1", ["x"], {"x": [-5, 5]}, threshold=1.0, n_random=5000)
    print(f"     status: {r2['status']} (best margin {r2.get('best_margin')})")
    if r2["status"] == "refuted":
        print("     FALSE REFUTATION of a true claim!")
        fails += 1
    else:
        print("     no counterexample in bounded search — claim survives (not proven).")

    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
