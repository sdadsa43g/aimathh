# Example session — pendulum: derive, simulate, verify

**User:** Derive the small-angle period of a pendulum and check it against a
real simulation.

**Harness (plan):** formulate → symbolic series → two simulations (5°, 60°) →
limiting-case checks → plot → present.

**Tool calls (abridged):**
1. `symbolic{op: series, expr: sin(theta), …}` → `θ - θ³/6 + O(θ⁴)`
2. `simulate{kind: ode, rhs: [w, -(g/L)·sin θ], …}` ×2 (5°, 60°)
3. `verify{limiting_case: measured-vs-2π√(L/g)}` → PASS at 5°, correctly FAIL at 60°
4. `visualize{kind: line, …}` → PNG artifact

**Result:** `NUMERICALLY_CONFIRMED` at 5° (0.07% error); the 60° mismatch is
presented as the expected breakdown of the approximation, with the nonlinear
simulation as the trusted value. See `demos/demo1_mechanics_derive_simulate.py`
for the runnable version.
