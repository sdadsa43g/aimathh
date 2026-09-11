"""Execution plans: the model proposes structure, tools produce facts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from aimathh.core.ids import new_id


class StepKind(str, Enum):
    FORMULATE = "formulate"
    TOOL = "tool"
    VERIFY = "verify"
    CRITIQUE = "critique"
    SYNTHESIZE = "synthesize"
    DEBATE = "debate"
    INVENT = "invent"


class PlanStep(BaseModel):
    id: str = ""
    kind: StepKind = StepKind.TOOL
    title: str = ""
    detail: str = ""
    tool: str = ""
    args: dict[str, Any] = Field(default_factory=dict)
    assignee: str = ""
    depends_on: list[str] = Field(default_factory=list)
    status: str = "pending"
    result_summary: str = ""


class ExecutionPlan(BaseModel):
    id: str = ""
    goal: str = ""
    assumptions: list[str] = Field(default_factory=list)
    steps: list[PlanStep] = Field(default_factory=list)

    @classmethod
    def create(cls, goal: str, steps: list[PlanStep], assumptions: list[str] | None = None) -> "ExecutionPlan":
        p = cls(id=new_id("plan_"), goal=goal, steps=steps, assumptions=assumptions or [])
        for s in p.steps:
            if not s.id:
                s.id = new_id("step_")
        return p

    @classmethod
    def default_plan(cls, goal: str) -> "ExecutionPlan":
        """Heuristic decomposition used when no model is configured.

        A real deployment replaces this with model-generated plans; the
        structure (formulate -> compute -> verify -> critique -> present)
        stays identical.
        """
        return cls.create(goal, [
            PlanStep(kind=StepKind.FORMULATE, title="Formulate problem",
                     detail="Restate the request with explicit assumptions and unknowns."),
            PlanStep(kind=StepKind.TOOL, title="Compute (primary route)",
                     detail="Run the primary computational route.", tool="python_exec"),
            PlanStep(kind=StepKind.VERIFY, title="Verify independently",
                     detail="Recompute via an independent route and compare."),
            PlanStep(kind=StepKind.CRITIQUE, title="Critique",
                     detail="Check limits, units, stability, alternatives."),
            PlanStep(kind=StepKind.SYNTHESIZE, title="Present",
                     detail="Produce the structured result with evidence labels."),
        ])
