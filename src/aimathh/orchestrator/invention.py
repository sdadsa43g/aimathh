"""Invention Mode pipeline: constraints -> concepts -> model -> simulate -> report.

The pipeline never declares "this invention works". It produces a structured
brief with mechanism, equations, predictions, simulations, failure modes and
a validation plan.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from aimathh.core.ids import new_id
from aimathh.orchestrator.agents import AgentContext, get_agent


class InventionBrief(BaseModel):
    id: str = ""
    problem: str = ""
    constraints: list[str] = Field(default_factory=list)
    existing_approaches: list[str] = Field(default_factory=list)
    failure_modes_prior: list[str] = Field(default_factory=list)
    concepts: list[dict[str, Any]] = Field(default_factory=list)
    selected_concept: str = ""
    mechanism: str = ""
    equations: list[str] = Field(default_factory=list)
    predictions: list[str] = Field(default_factory=list)
    simulations: list[dict[str, Any]] = Field(default_factory=list)
    expected_performance: str = ""
    failure_modes: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    validation_plan: list[str] = Field(default_factory=list)
    verdict: str = ""


async def run_invention_pipeline(
    problem: str,
    constraints: list[str],
    candidate_concepts: list[dict[str, Any]],
    simulations: list[dict[str, Any]] | None = None,
    project_id: str = "",
    seed: int | None = None,
) -> InventionBrief:
    """Execute the invention workflow. ``candidate_concepts`` come from the
    model or the user; everything from "Mathematical model" on is computed."""
    brief = InventionBrief(id=new_id("inv_"), problem=problem, constraints=constraints)
    brief.concepts = candidate_concepts
    if not candidate_concepts:
        brief.verdict = "No candidate concepts supplied — nothing to evaluate."
        return brief
    # Select: score by constraint coverage (explicit, auditable heuristic).
    scored = []
    for c in candidate_concepts:
        claimed = c.get("addresses", [])
        score = sum(1 for k in constraints if any(k.lower() in str(a).lower() or str(a).lower() in k.lower() for a in claimed))
        scored.append((score, c))
    scored.sort(key=lambda t: t[0], reverse=True)
    best = scored[0][1]
    brief.selected_concept = str(best.get("name", "concept-0"))
    brief.mechanism = str(best.get("mechanism", ""))
    brief.equations = [str(e) for e in best.get("equations", [])]
    # Simulate each proposed simulation spec for real.
    sim_agent = get_agent("simulation")
    for spec in simulations or best.get("simulations", []) or []:
        ctx = AgentContext(goal=f"invention sim: {brief.selected_concept}", project_id=project_id,
                           seed=seed, extra={"task": spec})
        try:
            res = await sim_agent.run(ctx)
            brief.simulations.append({"spec": spec, "summary": res.summary, "data_keys": list(res.data.keys())})
        except Exception as e:  # noqa: BLE001
            brief.simulations.append({"spec": spec, "error": str(e)})
    # Critic pass for failure modes
    critic = get_agent("critic")
    ctx = AgentContext(goal=problem, project_id=project_id, seed=seed,
                       extra={"task": {"limiting_cases": best.get("limiting_cases", [])}})
    res = await critic.run(ctx)
    brief.failure_modes = list(res.warnings) or ["No bounded failure found (not exhaustive)."]
    brief.unknowns = [str(u) for u in best.get("unknowns", [])] or [
        "Parameter values outside simulated ranges",
        "Unmodeled environmental coupling",
    ]
    brief.predictions = [str(p) for p in best.get("predictions", [])]
    brief.expected_performance = str(best.get("expected_performance", "Unknown — see simulations."))
    brief.validation_plan = [str(v) for v in best.get("validation_plan", [])] or [
        "Build minimal physical prototype of the selected concept",
        "Measure the predicted observable under controlled conditions",
        "Compare against simulation with calibrated parameters",
        "Stress-test predicted failure modes",
    ]
    brief.verdict = (
        f"Candidate '{brief.selected_concept}' modeled and simulated "
        f"({len(brief.simulations)} run(s)). This is a CANDIDATE with known unknowns — "
        "not a validated invention. See validation plan."
    )
    return brief
