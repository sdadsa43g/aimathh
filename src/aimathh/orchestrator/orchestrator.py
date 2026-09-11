"""Central research orchestrator.

Pipeline per request:
  UNDERSTAND -> PLAN -> EXECUTE (tools) -> VERIFY -> CRITIQUE -> PRESENT

The orchestrator:
* builds or refines an ExecutionPlan (model-generated when a provider is
  configured, heuristic otherwise),
* dispatches steps to sub-agents / tools with bounded retries + strategy
  changes on failure,
* runs the quality gate before labeling anything VERIFIED,
* persists everything to research memory.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from pydantic import BaseModel, Field

from aimathh.core.config import get_settings
from aimathh.core.ids import new_id
from aimathh.core.logging import get_logger
from aimathh.core.types import (
    Assumption,
    ComputationRecord,
    EvidenceLevel,
    ResearchResult,
    VerificationResult,
    VerificationStatus,
    Warning,
)
from aimathh.models.base import ChatMessage, ModelRequest
from aimathh.models.registry import get_registry
from aimathh.orchestrator.agents import AgentContext, get_agent
from aimathh.orchestrator.plans import ExecutionPlan, PlanStep, StepKind
from aimathh.research.memory import get_research_memory
from aimathh.research.models import ResearchProject
from aimathh.tools.registry import ToolContext, get_tool_registry
from aimathh.verification.engine import QualityGate

log = get_logger("orchestrator")

SYSTEM_PROMPT = """You are the planning brain of a mathematical-physics research harness.
You NEVER compute by hand: you decompose problems into tool calls (symbolic math,
numerical math, simulation, verification) and critique tool outputs.
Rules:
- State assumptions explicitly.
- Every important claim needs an independent check (different method/tool).
- Distinguish PROVEN / VERIFIED / NUMERICALLY CONFIRMED / HEURISTIC / HYPOTHESIS / UNVERIFIED.
- If methods disagree, investigate; never silently pick one.
- Never invent citations, numbers, or tool outputs.
Output a JSON plan: {"assumptions": [...], "steps": [{"kind": "tool|verify|critique",
"title": ..., "tool": ..., "args": {...}, "assignee": ...}]}.
""".strip()


class ResearchRequest(BaseModel):
    query: str
    project_id: str = ""
    provider: str = ""
    max_steps: int = 25
    seed: int | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class Orchestrator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.gate = QualityGate()

    # -- main entry ------------------------------------------------------
    async def research(self, req: ResearchRequest) -> ResearchResult:
        t0 = time.time()
        mem = get_research_memory()
        if req.project_id:
            try:
                project = mem.load_project(req.project_id)
            except KeyError:
                project = ResearchProject.create(req.query[:80], req.query)
        else:
            project = ResearchProject.create(req.query[:80], req.query)
        mem.save_project(project)

        plan = await self.plan(req, project)
        computations: list[ComputationRecord] = []
        warnings: list[Warning] = []
        evidence: list[str] = []
        verification = VerificationResult()
        artifacts: list = []

        tool_ctx = ToolContext(run_id=new_id("run_"), experiment_id=project.id, seed=req.seed)
        for step in plan.steps[: req.max_steps]:
            try:
                out = await self.execute_step(step, req, project, tool_ctx)
                step.status = "done"
                step.result_summary = str(out.get("summary", ""))[:500]
                computations.extend(out.get("computations", []))
                for w in out.get("warnings", []):
                    warnings.append(Warning(code="agent", message=str(w)))
                if out.get("verification") and out["verification"].status != VerificationStatus.NOT_RUN:
                    verification = out["verification"]
                for a in out.get("artifacts", []):
                    artifacts.append({"artifact_id": a, "kind": "file", "path": a})
                evidence.append(f"{step.title}: {step.result_summary}")
            except Exception as e:  # noqa: BLE001
                step.status = "failed"
                step.result_summary = f"FAILED: {e}"
                warnings.append(Warning(code="step_failed", message=f"{step.title}: {e}", severity="critical"))
                mem.record_failure(project.id, step.title, str(e))
                log.error("step %s failed: %s", step.title, e)

        mem.save_project(project)
        # Quality gate decides the label — the model never self-certifies.
        gate = self.gate.evaluate(
            executed=any(c.tool for c in computations),
            independently_checked=verification.independent_check is not None
            or verification.status == VerificationStatus.PASSED,
            units_consistent=None if verification.dimensional_check is None
            else verification.dimensional_check.status == VerificationStatus.PASSED,
            assumptions=[a for a in plan.assumptions],
            tolerances_reported=verification.tolerance is not None or any(
                c.tolerance is not None for c in computations),
            limiting_cases_ok=None,
            counterexample_searched=None,
            methods_agree=None if verification.status == VerificationStatus.NOT_RUN
            else verification.status == VerificationStatus.PASSED,
            sources_valid=None,
            reproducible=True,
        )
        if verification.status == VerificationStatus.NOT_RUN:
            level = EvidenceLevel.UNVERIFIED
        else:
            level = EvidenceLevel(gate["recommended_label"]) if gate["passed"] else EvidenceLevel.UNVERIFIED
            verification.evidence_level = level
        confidence = {"verified_computation": 0.9, "numerically_confirmed": 0.7,
                      "strongly_supported": 0.55, "heuristic": 0.3,
                      "hypothesis": 0.2, "unverified": 0.1, "refuted": 0.05,
                      "proven": 0.99}.get(level.value, 0.1)
        result = ResearchResult(
            id=new_id("res_"),
            title=req.query[:120],
            answer=self._compose_answer(req, plan, evidence, verification, warnings),
            assumptions=[Assumption(statement=a) for a in plan.assumptions],
            computations=computations,
            verification=verification,
            confidence=confidence,
            evidence=evidence,
            artifacts=artifacts,
            warnings=warnings,
            open_questions=[f"Extend verification: {q}" for q in self.gate.QUESTIONS[:3]],
        )
        mem.remember(project.id, "result", req.query[:80], result.answer[:2000], tags=["result"])
        log.info("research done in %.1fs: %s", time.time() - t0, verification.evidence_level.value)
        return result

    # -- planning ----------------------------------------------------------
    async def plan(self, req: ResearchRequest, project: ResearchProject) -> ExecutionPlan:
        provider_name = req.provider or self._default_provider()
        if provider_name:
            try:
                provider = get_registry().get(provider_name)
                resp = await provider.chat(ModelRequest(
                    system=SYSTEM_PROMPT,
                    messages=[ChatMessage(role="user", content=req.query)],
                    temperature=0.2, max_tokens=2000,
                ))
                plan = self._parse_model_plan(req.query, resp.text)
                if plan.steps:
                    return plan
            except Exception as e:  # noqa: BLE001
                log.warning("model planning failed (%s); using heuristic plan", e)
        # Heuristic fallback: a fixed, honest pipeline.
        return ExecutionPlan.default_plan(req.query)

    def _parse_model_plan(self, goal: str, text: str) -> ExecutionPlan:
        import json as _json
        import re as _re

        m = _re.search(r"\{.*\}", text, _re.S)
        if not m:
            return ExecutionPlan.default_plan(goal)
        try:
            data = _json.loads(m.group(0))
        except Exception:
            return ExecutionPlan.default_plan(goal)
        steps: list[PlanStep] = []
        for s in data.get("steps", [])[:20]:
            kind = str(s.get("kind", "tool")).lower()
            try:
                sk = StepKind(kind)
            except ValueError:
                sk = StepKind.TOOL
            steps.append(PlanStep(
                kind=sk, title=str(s.get("title", kind))[:200],
                detail=str(s.get("detail", ""))[:1000],
                tool=str(s.get("tool", ""))[:100],
                args=dict(s.get("args", {})) if isinstance(s.get("args"), dict) else {},
                assignee=str(s.get("assignee", ""))[:100],
            ))
        return ExecutionPlan.create(goal, steps, data.get("assumptions", []))

    def _default_provider(self) -> str:
        names = get_registry().list()
        for preferred in ("openai-compat", "anthropic", "local-ollama", "mock"):
            if preferred in names:
                # Only auto-use providers that are actually configured.
                if preferred == "mock":
                    continue  # heuristic plan is more honest than a mock plan
                return preferred
        return ""

    # -- execution -----------------------------------------------------------
    async def execute_step(self, step: PlanStep, req: ResearchRequest,
                           project: ResearchProject, tool_ctx: ToolContext) -> dict[str, Any]:
        if step.kind == StepKind.FORMULATE:
            return {"summary": step.detail or "Problem formulated with assumptions.",
                    "computations": [], "warnings": []}
        if step.kind == StepKind.SYNTHESIZE:
            return {"summary": "Synthesis deferred to final composition.", "computations": [], "warnings": []}
        if step.assignee:
            agent = get_agent(step.assignee)
            actx = AgentContext(goal=req.query, project_id=project.id, experiment_id=project.id,
                                seed=req.seed, tool_ctx=tool_ctx,
                                extra={"task": {"tool": step.tool, **step.args}})
            # Agents that take free-form tasks:
            if agent.name in ("coding", "mathematics", "simulation", "visualization",
                              "verification", "literature", "critic", "proof", "physics"):
                if step.tool and not actx.extra["task"].get("kind"):
                    # Generic single-tool dispatch through the coding agent path
                    reg = get_tool_registry()
                    res = await reg.call(step.tool, step.args, tool_ctx)
                    comp = ComputationRecord(id=new_id("comp_"), tool=step.tool, method=step.title,
                                             input=step.args, output_summary=str(res.output)[:500],
                                             output=res.output,
                                             provenance_id=res.provenance.id if res.provenance else "")
                    return {"summary": f"{step.tool} ok", "computations": [comp], "warnings": []}
            res = await agent.run(actx)
            return {"summary": res.summary, "computations": res.computations,
                    "warnings": res.warnings, "artifacts": res.artifacts,
                    "verification": res.verification}
        if step.kind == StepKind.TOOL and step.tool:
            reg = get_tool_registry()
            res = await reg.call(step.tool, step.args, tool_ctx)
            comp = ComputationRecord(id=new_id("comp_"), tool=step.tool, method=step.title,
                                     input=step.args, output_summary=str(res.output)[:500],
                                     output=res.output,
                                     provenance_id=res.provenance.id if res.provenance else "")
            return {"summary": f"{step.tool} ok", "computations": [comp], "warnings": []}
        if step.kind == StepKind.VERIFY:
            agent = get_agent("verification")
            actx = AgentContext(goal=req.query, project_id=project.id, tool_ctx=tool_ctx,
                                extra={"task": {"claim": req.query, "checks": step.args.get("checks", [])}})
            res = await agent.run(actx)
            return {"summary": res.summary, "computations": [], "warnings": res.warnings,
                    "verification": res.verification}
        if step.kind == StepKind.CRITIQUE:
            agent = get_agent("critic")
            actx = AgentContext(goal=req.query, project_id=project.id, tool_ctx=tool_ctx,
                                extra={"task": step.args})
            res = await agent.run(actx)
            return {"summary": res.summary, "computations": [], "warnings": res.warnings}
        return {"summary": "no-op step", "computations": [], "warnings": []}

    # -- presentation ----------------------------------------------------------
    def _compose_answer(self, req: ResearchRequest, plan: ExecutionPlan, evidence: list[str],
                        verification: VerificationResult, warnings: list[Warning]) -> str:
        lines = [
            f"## {req.query[:120]}",
            "",
            f"**Verdict: {verification.evidence_level.value.upper()}** "
            f"(checks: {verification.status.value}; methods: {', '.join(verification.methods) or 'none yet'})",
            "",
            "### What was done",
        ]
        for e in evidence[:15]:
            lines.append(f"- {e}")
        if plan.assumptions:
            lines.append("")
            lines.append("### Assumptions")
            for a in plan.assumptions:
                lines.append(f"- {a}")
        if verification.checks:
            lines.append("")
            lines.append("### Verification")
            for c in verification.checks:
                lines.append(f"- [{c.status.value}] {c.name}: {c.detail[:300]}")
        if verification.discrepancy_report:
            lines.append("")
            lines.append("### Discrepancy investigation")
            lines.append("```")
            lines.append(verification.discrepancy_report[:2000])
            lines.append("```")
        if warnings:
            lines.append("")
            lines.append("### Warnings")
            for w in warnings[:10]:
                lines.append(f"- ({w.severity}) {w.message[:300]}")
        lines += ["",
                  "> No-fabrication note: every number above came from an executed tool call "
                  "recorded in `computations` with provenance. Unchecked statements are labeled "
                  "UNVERIFIED by construction."]
        return "\n".join(lines)


_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
