# Verification Architecture

## Levels

| Level | Name | Implementation | Trust |
|-------|------|----------------|-------|
| L0 | Model reasoning | Plans, hypotheses, prose | **None.** Proposals only. |
| L1 | Symbolic | `math/symbolic.py` via SymPy: simplify/diff/integrate/solve/equals | Computer algebra; exact where decidable. |
| L2 | Numerical | `math/numeric.py` (mpmath arbitrary precision), SciPy routes, step-convergence studies, split-half MC checks | Tolerance-quantified agreement. |
| L3 | Dimensional/physical | `physics/dimensional.py` (dimension-only algebra over SymPy trees), limiting-case checks | Rejects invalid physics structurally. |
| L4 | Independent recomputation | `VerificationEngine.independent`: second implementation, different algorithm/library | Agreement required; disagreement → investigation. |
| L5 | Formal | `verification/formal.py`: Z3 backend (real, pip-installable); Lean/Coq/Isabelle detect toolchains and report honest status | Machine-checked where available. |

## Rules

1. **Two routes or it didn't happen.** Important quantities are computed at
   least twice via genuinely different paths (e.g. DOP853 vs Radau,
   SymPy vs mpmath, analytic vs simulation).
2. **Disagreement is a first-class event.** `DiscrepancyReport` with an
   investigation checklist (units → precision → assumptions → boundary
   conditions → tolerances → third algorithm → literature → minimal repro).
3. **Evidence ladder is enforced, not suggested.** `EvidenceLevel`:
   `PROVEN > VERIFIED_COMPUTATION > NUMERICALLY_CONFIRMED >
   STRONGLY_SUPPORTED > HEURISTIC > HYPOTHESIS > UNVERIFIED`, plus `REFUTED`.
   The `QualityGate` (11 questions) assigns the label; the model cannot
   self-certify.
4. **Universal claims get attacked.** `CounterexampleEngine` tries symbolic
   solving, grid/boundary sampling, random sampling, and adversarial
   optimization. A validated point REFUTES; no-find is labeled
   "bounded search, NOT a proof".
5. **Chaos and ill-conditioning are disclosed.** Solvers report conditioning,
   residuals, energy drift, and method agreement; chaotic systems (e.g. Lorenz)
   correctly fail pointwise agreement, and that is the *right* output.

## What "VERIFIED" means here

`VERIFIED_COMPUTATION` = executed + independently recomputed + agreed within
stated tolerance + dimensionally consistent (physics) + assumptions explicit +
reproducible (seed/env/manifest). It is not a formal proof; `PROVEN` is
reserved for machine-checked L5 results.
