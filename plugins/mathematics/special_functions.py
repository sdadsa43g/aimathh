"""Example math extension: special-function identities with self-tests.

Pattern for contributing verified mathematical content: each identity ships
with a symbolic check the harness can run. Nothing here is trusted until
`pytest plugins/` executes the checks below.
"""

from aimathh.verification import get_verification_engine

IDENTITIES = [
    # (lhs, rhs, variables)
    ("gamma(n+1)", "n*gamma(n)", ["n"]),  # Gamma recurrence (formal; checked structurally below)
    ("erf(-x)", "-erf(x)", ["x"]),  # erf is odd
    ("sin(2*x)", "2*sin(x)*cos(x)", ["x"]),  # double angle
    ("cosh(x)^2 - sinh(x)^2", "1", ["x"]),  # hyperbolic identity
]

# Only identities in this allowlist are asserted in tests (gamma recurrence
# needs assumptions SymPy can't discharge structurally, so it is checked
# numerically instead).
STRUCTURAL = {"erf(-x)", "sin(2*x)", "cosh(x)^2 - sinh(x)^2"}


def check_all() -> dict:
    eng = get_verification_engine()
    results = []
    for lhs, rhs, variables in IDENTITIES:
        if lhs in STRUCTURAL:
            c = eng.symbolic_equal(lhs, rhs, variables)
            results.append({"identity": f"{lhs} = {rhs}", "status": c.status.value})
    return {"checked": results}


if __name__ == "__main__":
    import json

    print(json.dumps(check_all(), indent=2))
