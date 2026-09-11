# AIMathH Architecture

## 1. Design philosophy

The AI model supplies **reasoning, planning, hypotheses, strategy, explanations**.
The harness supplies **exact computation, simulation, verification, rendering,
execution, reproducibility**. The pipeline is always:

```
MODEL → PLAN → COMPUTE → VERIFY → CROSS-CHECK → CRITIQUE → PRESENT
```

Nothing the model says about a number, equation, simulation, or citation is
trusted until a tool has executed and (for important claims) an independent
tool has agreed.

## 2. Repository layout

```
src/aimathh/
  core/            Settings, result objects (ResearchResult/VerificationResult),
                   provenance, typed errors, ids, structured logging
  models/          ModelProvider ABC + OpenAI-compat / Anthropic / Ollama / Mock
                   providers + capability registry with task routing
  tools/           Typed Tool registry (schemas, permissions, timeouts, stats,
                   provenance) + builtin/ adapters over every engine
  execution/       Sandbox (subprocess isolation, rlimits, timeouts), permission
                   model (READ/WRITE/EXECUTE/NETWORK/INSTALL), async job queue
  math/            symbolic (SymPy), numeric (mpmath), linalg, calculus,
                   ode, optimize, stats, transforms, nonlinear — all NumPy/SciPy
  physics/         units (Pint), constants (CODATA/SciPy), dimensional checker,
                   domain plugin registry (8 built-in domains)
  verification/    Levels-1..4 engine, quality gate, discrepancy reports,
                   counterexample engine, formal backends (Z3 real; Lean/Coq/
                   Isabelle honest stubs)
  simulation/      ODE/PDE/Monte-Carlo/sweep runners with diagnostics + replay
  visualization/   Plotly specs, matplotlib PNG fallback, Three.js scene graphs
  artifacts/       Content-addressed store (sha256, manifests)
  research/        Project/task/experiment/hypothesis/graph models, SQLite
                   memory, literature clients (arXiv + OpenAlex)
  orchestrator/    ExecutionPlan, sub-agents (9), central Orchestrator,
                   multi-agent debate, invention pipeline
  server/          FastAPI app: /v1/* typed endpoints, jobs, observability
  cli/             `aimathh` command (research/tool/verify/serve/demo)
  infrastructure/ In-process metrics
apps/web/          React + TS + Tailwind + KaTeX + Plotly + Three.js UI
plugins/           Out-of-tree examples: physics domain, math identities,
                   dataset generator, prover/visualization READMEs
tests/             unit/ integration/ benchmarks/ (adversarial included)
demos/             8 end-to-end demonstrations (all runnable, exit-coded)
docs/              This documentation set
examples/sessions/ Annotated transcripts of research sessions
```

## 3. Key data flow

1. **Request** arrives via CLI, API, or UI (`ResearchRequest{query,…}`).
2. **Orchestrator.plan** asks the model for a JSON plan (or uses the honest
   heuristic fallback when no provider is configured).
3. **Steps** dispatch to sub-agents or directly to tools. Every tool call:
   - checks permissions,
   - records a `Provenance` (tool, version, env, input, seed, deps, timing),
   - updates stats for observability.
4. **VerificationEngine** runs L1–L4 checks; failures produce
   `DiscrepancyReport`s, never silent averaging.
5. **QualityGate** evaluates 11 questions and assigns the only allowed
   verdict label (`PROVEN … UNVERIFIED … REFUTED`).
6. **ResearchResult** (structured, with computations/artifacts/citations/
   reproducibility) is returned and persisted to research memory.

## 4. Replaceability

| Concern      | Seam                                              |
|--------------|---------------------------------------------------|
| AI model     | `ModelProvider` + registry; routing by capability |
| Math backend | `math/*` modules wrap libraries; tools call modules, never libs directly |
| Units        | `physics/units.py` singleton; Pint can be swapped |
| Provers      | `formal.ProverBackend` interface                  |
| Job queue    | `execution/jobs.py` interface (swap for Redis/RQ) |
| Memory DB    | `research/memory.py` (SQLite today)               |
| Viz frontend | `PlotView` / `Scene3DView` / `Equation` components|
| API          | Versioned `/v1/*` FastAPI routers                 |

## 5. Why a single Python package (not 15 micro-packages)

`src/aimathh/*` mirrors the requested `packages/*` decomposition as modules
inside one versioned distribution. This keeps imports, dependency pins, and
refactors atomic at v0.1 while preserving every module boundary; splitting
into separately-published packages later is mechanical (each module already
has a single public `__init__` surface).
