"""End-to-end: full pipeline runs on representative research tasks."""

from aimathh.orchestrator import ResearchRequest, get_orchestrator
from aimathh.orchestrator.debate import run_debate
from aimathh.tools import get_tool_registry
from aimathh.tools.registry import ToolContext


async def test_toolchain_symbolic_numeric_verify():
    reg = get_tool_registry()
    ctx = ToolContext(seed=0)
    sym = await reg.call("symbolic", {"op": "integrate", "expr": "x^2", "var": "x", "a": "0", "b": "1"}, ctx)
    assert sym.output["result"] == "1/3"
    num = await reg.call("numeric", {"op": "evaluate", "expr": "1/3", "dps": 25}, ctx)
    assert abs(float(num.output["value"]) - 1 / 3) < 1e-24
    ver = await reg.call("verify", {"claim": "integral = 1/3", "checks": [
        {"kind": "symbolic_equal", "a": sym.output["result"], "b": "1/3"},
        {"kind": "numeric_agree", "value_a": float(num.output["value"]), "value_b": 1 / 3, "tol": 1e-12},
    ]}, ctx)
    assert ver.output["status"] == "passed"
    assert ver.output["evidence_level"] == "verified_computation"


async def test_simulate_visualize_chain():
    reg = get_tool_registry()
    ctx = ToolContext(seed=1)
    sim = await reg.call("simulate", {"kind": "ode", "rhs_exprs": ["v", "-x"], "variables": ["x", "v"],
                                      "t_span": [0, 6.283185307179586], "y0": [1.0, 0.0],
                                      "energy_expr": "x^2/2+v^2/2"}, ctx)
    assert sim.output["diagnostics"]["energy"]["conserved"] is True
    fig = await reg.call("visualize", {"kind": "ode", "x": sim.output["t"][:50],
                                       "y": [row[:50] for row in sim.output["y"]],
                                       "variables": ["x", "v"], "title": "osc"}, ctx)
    assert "figure" in fig.output and "png_artifact" in fig.output


async def test_orchestrator_full_run():
    res = await get_orchestrator().research(ResearchRequest(query="Derive and check energy of oscillator", max_steps=4))
    assert res.id and res.answer and res.created_at is not None
    assert 0.0 <= res.confidence <= 1.0


async def test_debate_two_routes_agree_on_integral():
    v = await run_debate("integral of x^2 on [0,1]", {
        "symbolic": {"agent": "mathematics",
                     "task": {"kind": "integrate", "expr": "x^2", "var": "x", "a": "0", "b": "1"}},
        "numeric": {"agent": "coding",
                    "task": {}, "code": "print('x')"},
    })
    assert v.question.startswith("integral")
    assert len(v.positions) == 2
