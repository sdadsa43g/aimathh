# Roadmap

## Shipped (v0.1 — this repo)

- Phase 1: core architecture, model abstraction + 4 providers, tool registry
  (20 tools), sandbox, API, UI shell, structured results, provenance.
- Phase 2: symbolic/numeric/linalg/calculus/ODE/optimize/stats/transforms/
  nonlinear engines, units + CODATA constants, L1–L4 verification engine,
  quality gate, counterexample engine, Plotly + PNG + notebook-ready outputs.
- Phase 3: 8 physics domains, ODE/heat-PDE/Monte-Carlo/sweep simulators,
  3D scene graphs + Three.js viewer, parameter sweeps.
- Phase 4: research projects/memory (SQLite), research graph, arXiv+OpenAlex
  literature with provenance, citations.
- Phase 5 (partial): 9 sub-agents, multi-agent debate, invention pipeline,
  Z3 backend (real), Lean/Coq/Isabelle detection + honest stubs.
- Phase 6 (partial): optimization suite, job queue, artifact store,
  8 runnable demos, benchmark suite with adversarial rejection tests.

## Next (v0.2)

- [ ] Model-driven planning wired end-to-end with a live provider + prompt
      regression tests; plan repair loop (failed step → replan, bounded).
- [ ] Notebook engine: `.ipynb` generation/execution (`nbclient`), replayable
      session notebooks as artifacts.
- [ ] PDE expansion: 2-D heat/wave (method of lines), FEniCSx adapter behind
      the simulator interface.
- [ ] GPU/JAX adapters: `math` backends for `jax.numpy` + `torch` where
      beneficial; keep NumPy as the verified baseline (L4 pairs).
- [ ] Units v2: uncertainty propagation (`uncertainties`-style), natural units.

## Later (v0.3+)

- [ ] L5 elaborated: Lean 4 lake-project scaffolding + tactic-block checking;
      Coq/Isabelle runners; proof-state caching.
- [ ] Distributed execution: Redis-backed job queue, worker pool, GPU labels,
      checkpoint/resume across restarts.
- [ ] Bayesian inference expansion (MCMC adapter), symbolic regression for
      "find the law" workflows, dataset versioning (DVC-style manifests).
- [ ] CAD/STL/VTK exporters, animation rendering (webm), report PDFs (LaTeX).
- [ ] Multi-user auth, per-project secrets, audit log, rate limits.
- [ ] Advanced domains: GR tensors (EinsteinPy adapter), QFT helpers, plasma,
      control theory, category-theory proof sketches.

## Explicit non-goals

- Replacing mature libraries (no home-grown CAS/solver/plotter).
- Letting the model self-certify: the quality gate stays code, not prose.
