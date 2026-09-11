"""Sub-agent framework. Agents orchestrate tools; they never answer from prose.

Each agent receives an :class:`AgentContext` (goal, project, tool access) and
returns an :class:`AgentResult` with computations + verification attached.
Model-backed reasoning plugs in via ``brain``; without a model, agents run
deterministic tool pipelines so the harness is useful offline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from aimathh.core.ids import new_id
from aimathh.core.logging import get_logger
from aimathh.core.types import ComputationRecord, ResearchResult, VerificationResult
from aimathh.tools.registry import ToolContext, get_tool_registry

log = get_logger("agents")


class AgentContext(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    goal: str
    project_id: str = ""
    experiment_id: str = ""
    seed: int | None = None
    budget_steps: int = 25
    tool_ctx: ToolContext | None = None
    brain: Any = None  # ModelProvider or None
    extra: dict[str, Any] = Field(default_factory=dict)

    def tools(self) -> ToolContext:
        if self.tool_ctx is None:
            self.tool_ctx = ToolContext(run_id=new_id("run_"), experiment_id=self.experiment_id,
                                        seed=self.seed)
        return self.tool_ctx


class AgentResult(BaseModel):
    agent: str
    summary: str
    computations: list[ComputationRecord] = Field(default_factory=list)
    verification: VerificationResult = Field(default_factory=VerificationResult)
    artifacts: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class Agent(ABC):
    name: str = "base"
    description: str = ""

    @abstractmethod
    async def run(self, ctx: AgentContext) -> AgentResult:
        raise NotImplementedError

    # -- helpers ---------------------------------------------------------
    async def call_tool(self, ctx: AgentContext, name: str, args: dict[str, Any]) -> Any:
        reg = get_tool_registry()
        res = await reg.call(name, args, ctx.tools())
        if not res.ok:
            raise RuntimeError(f"Tool {name} failed: {res.error}")
        return res.output

    def record(self, tool: str, method: str, args: dict, output: Any, prov_id: str = "") -> ComputationRecord:
        import json as _json

        try:
            summary = _json.dumps(output, default=str)[:500]
        except Exception:
            summary = str(output)[:500]
        return ComputationRecord(id=new_id("comp_"), tool=tool, method=method,
                                 input=args, output_summary=summary, output=output,
                                 provenance_id=prov_id)


_AGENTS: dict[str, Agent] = {}


def register_agent(agent: Agent) -> None:
    _AGENTS[agent.name] = agent


def get_agent(name: str) -> Agent:
    if name not in _AGENTS:
        raise KeyError(f"Unknown agent '{name}'. Known: {sorted(_AGENTS)}")
    return _AGENTS[name]


def list_agents() -> list[dict[str, str]]:
    return [{"name": a.name, "description": a.description} for a in _AGENTS.values()]


# ----------------------------------------------------------------- agents
class MathematicsAgent(Agent):
    name = "mathematics"
    description = "Symbolic + numeric mathematics via trusted engines."

    async def run(self, ctx: AgentContext) -> AgentResult:
        task = ctx.extra.get("task", {})
        kind = task.get("kind", "simplify")
        if kind == "simplify":
            out = await self.call_tool(ctx, "symbolic", {"op": "simplify", "expr": task["expr"]})
        elif kind == "solve":
            out = await self.call_tool(ctx, "symbolic", {"op": "solve", "expr": task["expr"], "var": task["var"]})
        elif kind == "integrate":
            out = await self.call_tool(ctx, "symbolic", {"op": "integrate", "expr": task["expr"], "var": task["var"],
                                                       "a": task.get("a"), "b": task.get("b")})
        elif kind == "evaluate":
            out = await self.call_tool(ctx, "numeric", {"op": "evaluate", "expr": task["expr"],
                                                        "variables": task.get("variables", {}),
                                                        "dps": task.get("dps", 30)})
        else:
            out = await self.call_tool(ctx, "python_exec", {"code": task.get("code", "print('noop')")})
        return AgentResult(agent=self.name, summary=f"math:{kind} done",
                           computations=[self.record("math", kind, task, out)])


class PhysicsAgent(Agent):
    name = "physics"
    description = "Physics formulation + dimensional validation + constants."

    async def run(self, ctx: AgentContext) -> AgentResult:
        task = ctx.extra.get("task", {})
        equation = task.get("equation", "")
        symbols = task.get("symbols", {})
        dims = await self.call_tool(ctx, "dimensional_check", {"equation": equation, "symbols": symbols})
        return AgentResult(agent=self.name,
                           summary=f"dimensional: {'consistent' if dims['consistent'] else 'MISMATCH'}",
                           computations=[self.record("dimensional_check", "L3", task, dims)])


class VerificationAgent(Agent):
    name = "verification"
    description = "Independent verification of claims (L1-L4)."

    async def run(self, ctx: AgentContext) -> AgentResult:
        from aimathh.verification import get_verification_engine

        task = ctx.extra.get("task", {})
        eng = get_verification_engine()
        outcomes = []
        for c in task.get("checks", []):
            k = c["kind"]
            if k == "symbolic_equal":
                outcomes.append(eng.symbolic_equal(c["a"], c["b"], c.get("variables")))
            elif k == "numeric_agree":
                outcomes.append(eng.numeric_agree(c["value_a"], c["value_b"], tol=c.get("tol", 1e-8)))
            elif k == "dimensional":
                outcomes.append(eng.dimensional(c["equation"], c["symbols"]))
            elif k == "limiting_case":
                outcomes.append(eng.limiting_case(c.get("label", "?"), c["computed"], c["expected"]))
        vr = eng.verify_claim(task.get("claim", ctx.goal), outcomes)
        return AgentResult(agent=self.name, summary=f"verification: {vr.status.value}/{vr.evidence_level.value}",
                           verification=vr)


class SimulationAgent(Agent):
    name = "simulation"
    description = "ODE/PDE/Monte Carlo simulation with diagnostics."

    async def run(self, ctx: AgentContext) -> AgentResult:
        task = ctx.extra.get("task", {})
        out = await self.call_tool(ctx, "simulate", task)
        return AgentResult(agent=self.name, summary=f"simulation {task.get('kind')} done",
                           computations=[self.record("simulate", str(task.get("kind")), task,
                                                     {k: (v if k != 'y' else f"<{len(v)} series>") for k, v in out.items()})],
                           data=out)


class VisualizationAgent(Agent):
    name = "visualization"
    description = "Figures and 3D scenes from computed data."

    async def run(self, ctx: AgentContext) -> AgentResult:
        task = ctx.extra.get("task", {})
        out = await self.call_tool(ctx, "visualize", task)
        arts = [out["png_artifact"]["id"]] if "png_artifact" in out else []
        return AgentResult(agent=self.name, summary="figure built", artifacts=arts, data={"figure": out.get("figure")})


class LiteratureAgent(Agent):
    name = "literature"
    description = "Paper search + retrieval with provenance."

    async def run(self, ctx: AgentContext) -> AgentResult:
        from aimathh.execution.permissions import Permission

        # Explicit, logged escalation: this agent's sole purpose is network
        # retrieval through the harness HTTP client (never from the sandbox).
        ctx.tools().permissions.allowed.add(Permission.NETWORK)
        log.info("literature agent granted NETWORK for retrieval")
        q = ctx.extra.get("query", ctx.goal)
        out = await self.call_tool(ctx, "literature_search", {"query": q, "max_results": 8})
        return AgentResult(agent=self.name, summary=f"{out['count']} sources retrieved", data=out)


class CriticAgent(Agent):
    name = "critic"
    description = "Adversarial review: limits, units, stability, alternatives."

    async def run(self, ctx: AgentContext) -> AgentResult:
        from aimathh.verification import get_counterexample_engine

        task = ctx.extra.get("task", {})
        warnings: list[str] = []
        data: dict[str, Any] = {}
        # 1. Counterexample probe when a universal claim is supplied
        claim = task.get("universal_claim")
        if claim:
            rep = get_counterexample_engine().attack(
                claim["predicate"], claim["variables"], claim["bounds"],
                relation=claim.get("relation", ">="), threshold=claim.get("threshold", 0.0))
            data["counterexample_probe"] = rep
            if rep["status"] == "refuted":
                warnings.append(f"Claim REFUTED at {rep['counterexample']}")
        # 2. Limiting cases
        for lc in task.get("limiting_cases", []):
            from aimathh.verification import get_verification_engine

            oc = get_verification_engine().limiting_case(lc["label"], lc["computed"], lc["expected"], lc.get("tol", 1e-6))
            data.setdefault("limiting_cases", []).append(oc.model_dump())
            if oc.status.value != "passed":
                warnings.append(f"Limiting case violated: {lc['label']}")
        if not warnings:
            warnings.append("No issues found by bounded critic probes (not exhaustive).")
        return AgentResult(agent=self.name, summary=f"critic: {len(warnings)} finding(s)",
                           warnings=warnings, data=data)


class CodingAgent(Agent):
    name = "coding"
    description = "Scientific software: write, execute, debug in sandbox."

    async def run(self, ctx: AgentContext) -> AgentResult:
        code = ctx.extra.get("code", "print('hello')")
        out = await self.call_tool(ctx, "python_exec", {"code": code, "seed": ctx.seed})
        ok = out.get("success", False)
        return AgentResult(agent=self.name, summary=f"code {'ran OK' if ok else 'FAILED'}",
                           computations=[self.record("python_exec", "run", {"code": code[:500]}, out)],
                           warnings=[] if ok else [out.get("stderr", "")[-500:]])


class ProofAgent(Agent):
    name = "proof"
    description = "Proof strategy + formal backend status. Never claims unproven results."

    async def run(self, ctx: AgentContext) -> AgentResult:
        from aimathh.verification import formal

        backs = [c.model_dump() for c in formal.list_backends()]
        avail = [b for b in backs if b["available"]]
        return AgentResult(
            agent=self.name,
            summary=f"formal backends available: {[b['name'] for b in avail] or 'none'}",
            data={"backends": backs},
            warnings=["No machine-checked proof produced in this run; label accordingly."],
        )


for _a in (MathematicsAgent(), PhysicsAgent(), VerificationAgent(), SimulationAgent(),
           VisualizationAgent(), LiteratureAgent(), CriticAgent(), CodingAgent(), ProofAgent()):
    register_agent(_a)
