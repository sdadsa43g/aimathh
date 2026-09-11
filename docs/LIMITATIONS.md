# Known Limitations (v0.1)

Honest accounting — every item here is a roadmap candidate, not a hidden gap.

1. **Planner without a model is heuristic.** With no provider configured, the
   orchestrator runs a fixed formulate→compute→verify pipeline rather than
   true adaptive planning. Results stay labeled UNVERIFIED until real checks
   run — the safe failure mode.
2. **Sandbox is process-level, not kernel-level.** Timeouts, memory rlimits,
   and filesystem isolation are enforced; network-namespace/seccomp isolation
   is not. Use containers for untrusted workloads.
3. **Symbolic coverage = SymPy coverage.** Unevaluated integrals, hard PDEs,
   and undecidable equivalences are reported as such (`unevaluated: true`),
   never papered over.
4. **L5 formal proving is scaffolded.** Z3 works when installed; Lean/Coq/
   Isabelle report toolchain presence and stop there. Nothing is labeled
   PROVEN by this release.
5. **Literature needs network + services.** arXiv/OpenAlex clients degrade to
   empty results with warnings when unreachable; the no-fabrication rule then
   forbids literature-backed conclusions (see Demo 5).
6. **PDE scope is 1-D heat + ODE systems.** Higher-dimensional/constrained
   PDEs arrive in v0.2 behind the same simulator interface.
7. **No built-in user auth.** Single-operator / trusted-proxy deployments only.
8. **Frontend is a vertical slice.** Research/Lab/Visualize/Ops tabs cover the
   core loop; notebook editing, terminal, and CAD viewers are future work.
9. **Job queue is in-process.** Jobs don't survive restarts; Redis backing is
   planned (interface is already abstracted).
10. **Units for user symbols are mandatory.** The dimensional checker refuses
    to guess — every symbol needs explicit units (`dimensionless` allowed).
    Names colliding with SymPy builtins (E, gamma, …) are handled by forced
    symbol parsing, but exotic notation may need normalization first.
