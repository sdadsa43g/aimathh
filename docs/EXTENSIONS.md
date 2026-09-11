# Extension & Plugin Guide

## Add a tool (5 minutes)

```python
from aimathh.tools.registry import tool

@tool("my_tool", "What it does. Be precise — the model reads this.",
      input_schema={"type": "object",
                    "properties": {"x": {"type": "number"}},
                    "required": ["x"]},
      tags=["math"])
def _my_tool(args, ctx):
    from aimathh.myengine import compute
    return compute(args["x"])   # must be JSON-serializable
```

Import the module once (e.g. from `tools/builtin.py` or a plugin loader)
and the tool appears in `/v1/tools`, the model tool list, and the UI.

Rules: keep logic in a tested engine module; the tool only shapes arguments;
every output must be reproducible (accept `ctx.seed` where randomness applies).

## Add a physics domain

See `plugins/physics/optics_extended.py`: build a `DomainPlugin` with
equations (sympy-parseable `expression` + `symbols` units map), constants,
assumptions, validation rules, references — then `get_domain_registry().register(p)`.
Equations with full unit maps are immediately checkable by `dimensional_check`.

## Add a model provider

Subclass `ModelProvider` (`chat()` + `capabilities()`), register it, and add
config keys to `core/config.py`. Routing uses `Capability` + reliability
scores; see `models/openai_compat.py` for the reference implementation.

## Add a prover backend (L5)

Subclass `formal.ProverBackend`; report `available=False` with an install hint
when the toolchain is missing; register in `formal._BACKENDS`. See
`plugins/theorem-proving/README.md`.

## Add a visualization

Backend: emit a Plotly spec (`visualization/plots.py`) or extend `Scene3D`
(`visualization/scene3d.py`). Frontend: extend `Scene3DView.tsx` /
`PlotView.tsx`. Ship a test asserting buffers equal computed inputs.

## Add a benchmark

Append exact-answer cases (and adversarial wrong-answer rejections) to
`tests/benchmarks/test_benchmarks.py`. Benchmarks are the harness's immune
system — every new engine needs at least one.
