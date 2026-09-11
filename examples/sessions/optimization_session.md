# Example session — engineering optimization with two-route verification

**User:** Design a 1-liter cylindrical can using minimum material.

**Harness (plan):** analytic derivation (SymPy) → numeric optimization
(L-BFGS-B + differential evolution) → agreement checks → sensitivity → present.

**Tool calls (abridged):**
1. `symbolic{op: diff, expr: 2πr² + 2V/r}` → stationary condition
2. `optimize{op: minimize, …}` → r ≈ 5.42 cm, h ≈ 10.84 cm
3. `optimize{op: global, …}` → agrees to 4 decimals
4. `verify{numeric_agree ×2, limiting_case h=2r}` → PASSED
5. `optimize{op: sensitivity, …}` → r-share 4/3, h-share 2/3

**Result:** `NUMERICALLY_CONFIRMED`, r* ≈ 5.42 cm, h* ≈ 10.84 cm (h = 2r),
with the penalty-formulation assumptions stated. Runnable:
`demos/demo7_engineering_optimization.py`.
