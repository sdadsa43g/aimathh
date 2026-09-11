"""Multi-agent debate: independent attacks, evidence-based verdict.

Agents A..F pursue different strategies; the Judge resolves conflicts through
computation/evidence — never by averaging numbers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from aimathh.core.ids import new_id
from aimathh.core.types import EvidenceLevel
from aimathh.orchestrator.agents import AgentContext, get_agent


class DebateVerdict(BaseModel):
    id: str = ""
    question: str = ""
    positions: list[dict[str, Any]] = Field(default_factory=list)
    agreements: list[str] = Field(default_factory=list)
    disagreements: list[str] = Field(default_factory=list)
    verdict: str = ""
    evidence_level: EvidenceLevel = EvidenceLevel.UNVERIFIED
    resolution_method: str = ""


class Debate(BaseModel):
    id: str = ""
    question: str = ""
    strategies: list[str] = Field(default_factory=list)
    verdict: DebateVerdict | None = None


async def run_debate(question: str, strategies: dict[str, dict[str, Any]],
                     project_id: str = "", seed: int | None = None) -> DebateVerdict:
    """Run each strategy's agent independently, then judge.

    ``strategies`` maps a label (e.g. 'analytical') to
    ``{'agent': 'mathematics', 'task': {...}}``.
    """
    debate = Debate(id=new_id("debate_"), question=question, strategies=list(strategies))
    positions: list[dict[str, Any]] = []
    for label, spec in strategies.items():
        agent = get_agent(spec.get("agent", "mathematics"))
        ctx = AgentContext(goal=question, project_id=project_id, seed=seed,
                           extra={"task": spec.get("task", {})})
        try:
            res = await agent.run(ctx)
            positions.append({"strategy": label, "agent": agent.name, "summary": res.summary,
                              "data": res.data, "computations": [c.model_dump() for c in res.computations],
                              "warnings": res.warnings, "ok": True})
        except Exception as e:  # noqa: BLE001
            positions.append({"strategy": label, "agent": agent.name, "summary": f"FAILED: {e}",
                              "ok": False})
    # Judge: compare numeric claims across positions when present.
    verdict = _judge(question, positions)
    debate.verdict = verdict
    return verdict


def _judge(question: str, positions: list[dict[str, Any]]) -> DebateVerdict:
    ok = [p for p in positions if p.get("ok")]
    failed = [p for p in positions if not p.get("ok")]
    # Collect scalar claims
    scalars: dict[str, list[float]] = {}
    for p in ok:
        for key in ("value", "result", "root", "fun"):
            v = p.get("data", {}).get(key)
            if isinstance(v, (int, float)):
                scalars.setdefault(key, []).append(float(v))
    agreements, disagreements = [], []
    for key, vals in scalars.items():
        if len(vals) >= 2:
            spread = max(vals) - min(vals)
            scale = max(1.0, max(abs(v) for v in vals))
            if spread / scale < 1e-6:
                agreements.append(f"{key}: {len(vals)} methods agree to {spread:.2e}")
            else:
                disagreements.append(f"{key}: spread {spread:.3e} across {vals} — DISCREPANCY, needs investigation")
    if disagreements:
        verdict_text = ("Methods DISAGREE. No averaged answer is given. " + " ".join(disagreements))
        level = EvidenceLevel.UNVERIFIED
        method = "contradiction flagged for discrepancy investigation"
    elif agreements:
        verdict_text = "Independent strategies agree. " + " ".join(agreements)
        level = EvidenceLevel.VERIFIED_COMPUTATION
        method = "independent agreement across strategies"
    elif ok:
        verdict_text = f"{len(ok)} strategie(s) completed without comparable scalars; manual review needed."
        level = EvidenceLevel.HEURISTIC
        method = "single-strategy completion"
    else:
        verdict_text = f"All strategies failed: {[p['summary'] for p in failed]}"
        level = EvidenceLevel.UNVERIFIED
        method = "all failed"
    return DebateVerdict(
        id=new_id("verdict_"), question=question, positions=positions,
        agreements=agreements, disagreements=disagreements,
        verdict=verdict_text, evidence_level=level, resolution_method=method,
    )
