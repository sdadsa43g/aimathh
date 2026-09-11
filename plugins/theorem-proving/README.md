# Theorem-proving plugins (roadmap)

Level-5 integrations live behind `aimathh.verification.formal.ProverBackend`.
To add a prover:

1. Subclass `ProverBackend` with `name`, `capabilities()` and `check(problem)`.
2. `capabilities()` must report `available=False` + `install_hint` when the
   toolchain is absent — never fake a proof.
3. `check()` receives a JSON problem, e.g. `{"kind": "smt2", "smt2": "..."}` for
   SMT solvers or `{"kind": "lean", "code": "...", "project": "..."}` for Lean.
4. Register in `formal._BACKENDS` and add a `plugins/theorem-proving/<name>.py`
   module plus tests asserting honest unavailability without the toolchain.

Current status:

| Backend  | Status                                  |
|----------|-----------------------------------------|
| Z3       | Implemented (works when `z3-solver` pip package installed) |
| Lean 4   | Detects `lean` binary; elaborated pipeline on roadmap |
| Coq      | Detects `coqc` binary; pipeline on roadmap |
| Isabelle | Detects `isabelle` binary; pipeline on roadmap |

See `docs/ROADMAP.md` for the phased plan.
