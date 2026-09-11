# AIMathH — Universal Mathematical & Physics AI Research Harness

Turn an arbitrary AI model into a computational research agent:

```
MODEL → PLAN → COMPUTE → VERIFY → CROSS-CHECK → CRITIQUE → PRESENT
```

The model reasons and plans; **trusted engines compute and verify**. Nothing
the model claims about a number, equation, simulation, or citation is
presented as verified until tools have executed and independent checks agree.

## What it does

- **Mathematics**: symbolic algebra (SymPy), arbitrary precision (mpmath),
  linear algebra, calculus, ODEs, optimization, statistics, Fourier/Laplace,
  nonlinear systems, dynamical systems — every engine wrapped with
  residual/convergence diagnostics.
- **Physics**: Pint units, CODATA constants, dimensional gate that *rejects*
  invalid equations, 8 domain plugins (mechanics, EM, thermo, QM, relativity,
  fluids, optics, astro).
- **Verification (L1–L5)**: symbolic equality, high-precision recomputation,
  dimensional + limiting-case checks, independent second implementations,
  counterexample search, quality gate with an enforced evidence ladder
  (`PROVEN … VERIFIED … UNVERIFIED … REFUTED`); Z3 backend real, Lean/Coq/
  Isabelle honestly stubbed.
- **Simulation**: ODE/PDE/Monte-Carlo/sweeps with conservation diagnostics
  and replay manifests; async job queue for long runs.
- **Research**: projects, SQLite memory, research graph, arXiv+OpenAlex
  literature with provenance, 9 sub-agents, multi-agent debate, invention
  pipeline (candidates, never false claims of success).
- **Interfaces**: typed FastAPI (`/v1/*`), `aimathh` CLI, React+KaTeX+Plotly+
  Three.js UI, content-addressed artifact store.

## Quickstart

```bash
pip install -e .[dev]
make test                 # 115+ tests incl. adversarial benchmarks
python demos/demo1_mechanics_derive_simulate.py
make server               # API :8000  (separate shell)
cd apps/web && npm install && npm run dev   # UI :5173
```

Optional model providers via `.env` (works fully offline without them):

```bash
cp .env.example .env   # OPENAI_API_KEY / ANTHROPIC_API_KEY / LOCAL_MODEL (Ollama)
```

## Demos (all runnable, exit-coded)

| # | Script | Shows |
|---|--------|-------|
| 1 | `demos/demo1_mechanics_derive_simulate.py` | Derive pendulum theory, simulate nonlinear truth, compare |
| 2 | `demos/demo2_ode_multi_method.py` | ODE via dsolve + DOP853 + Radau → VERIFIED |
| 3 | `demos/demo3_dimensional_reject.py` | Dimensional gate: 8/8 accept/reject correct |
| 4 | `demos/demo4_counterexample.py` | Refute false conjecture, spare true one |
| 5 | `demos/demo5_literature_research.py` | arXiv/OpenAlex investigation w/ provenance |
| 6 | `demos/demo6_interactive_3d.py` | 3D scene graph + interactive HTML artifact |
| 7 | `demos/demo7_engineering_optimization.py` | Optimal can: analytic + numeric agree |
| 8 | `demos/demo8_invention_report.py` | Invention brief: model → simulate → validate-plan |

## Docs

- `docs/ARCHITECTURE.md` — system design, layout, data flow, seams
- `docs/VERIFICATION.md` — L0–L5, evidence ladder, quality gate
- `docs/SECURITY.md` — permissions, sandbox, deployment guidance
- `docs/DEPLOYMENT.md` — local/Docker/production, CLI reference
- `docs/EXTENSIONS.md` — add tools, domains, providers, provers, benchmarks
- `docs/ROADMAP.md` — shipped vs next (notebooks, PDEs, L5, GPU, auth)
- `docs/LIMITATIONS.md` — honest v0.1 gaps
- `examples/sessions/` — annotated research transcripts

## Principles (enforced in code, not prose)

- Never rely on the model alone for mathematics.
- Two independent routes or it didn't happen; disagreement → investigation.
- The quality gate assigns verdict labels; the model cannot self-certify.
- No fabricated calculations, citations, or tool outputs — ever.
