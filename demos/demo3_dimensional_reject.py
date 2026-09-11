"""Demo 3 — Dimensional analysis accepts valid physics, rejects invalid physics.

A hallucinated equation (E = m c) must be REJECTED before it could ever be
presented; the correct forms must PASS. Exits non-zero on any misclassification.
"""

import sys

from aimathh.physics.dimensional import check_equation

CASES = [
    # (equation, symbols, expected_consistent)
    ("F = m*a", {"F": "newton", "m": "kg", "a": "m/s^2"}, True),
    ("E = m*c^2", {"E": "joule", "m": "kg", "c": "m/s"}, True),
    ("E = m*c", {"E": "joule", "m": "kg", "c": "m/s"}, False),  # the hallucination
    ("T = (1/2)*m*v^2", {"T": "joule", "m": "kg", "v": "m/s"}, True),
    ("T = (1/2)*m*v", {"T": "joule", "m": "kg", "v": "m/s"}, False),
    ("p + rho*v^2/2 + rho*g*h = C",
     {"p": "pascal", "rho": "kg/m^3", "v": "m/s", "g": "m/s^2", "h": "m", "C": "pascal"}, True),
    ("v = H0*d", {"v": "m/s", "H0": "1/s", "d": "m"}, True),
    ("L = 4*pi*R^2*sigma*T^3",  # wrong Stefan-Boltzmann exponent
     {"L": "watt", "R": "m", "sigma": "W/(m^2 K^4)", "T": "kelvin", "pi": "dimensionless"}, False),
]


def main() -> None:
    print("=" * 72)
    print("DEMO 3: dimensional gate — accept truth, reject hallucinations")
    print("=" * 72)
    fails = 0
    for eq, syms, expected in CASES:
        r = check_equation(eq, syms)
        ok = r.consistent == expected
        fails += not ok
        flag = "ACCEPT" if r.consistent else "REJECT"
        print(f"\n[{flag}] {eq}")
        print(f"       expected={'accept' if expected else 'reject'} -> {'OK' if ok else 'MISCLASSIFIED!'}")
        if not r.consistent:
            print(f"       {r.detail[:160]}")
    print(f"\n{len(CASES) - fails}/{len(CASES)} classified correctly.")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
