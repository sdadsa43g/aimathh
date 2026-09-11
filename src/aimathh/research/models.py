"""Project / task / experiment / hypothesis / graph models."""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from aimathh.core.ids import new_id
from aimathh.core.types import Citation, EvidenceLevel, ResearchResult, VerificationResult


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"


class Hypothesis(BaseModel):
    id: str = ""
    statement: str
    status: EvidenceLevel = EvidenceLevel.HYPOTHESIS
    supporting: list[str] = Field(default_factory=list)
    refuting: list[str] = Field(default_factory=list)
    created_at: float = 0.0


class Experiment(BaseModel):
    id: str = ""
    title: str = ""
    method: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    result_summary: str = ""
    verification: VerificationResult = Field(default_factory=VerificationResult)
    artifacts: list[str] = Field(default_factory=list)
    seed: int | None = None
    created_at: float = 0.0


class ResearchTask(BaseModel):
    id: str = ""
    title: str = ""
    detail: str = ""
    status: TaskStatus = TaskStatus.PENDING
    assignee: str = ""  # agent name
    depends_on: list[str] = Field(default_factory=list)
    result: ResearchResult | None = None
    created_at: float = 0.0


class ResearchProject(BaseModel):
    id: str = ""
    title: str = ""
    goal: str = ""
    assumptions: list[str] = Field(default_factory=list)
    tasks: list[ResearchTask] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    experiments: list[Experiment] = Field(default_factory=list)
    conclusions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0

    @classmethod
    def create(cls, title: str, goal: str) -> "ResearchProject":
        now = time.time()
        return cls(id=new_id("proj_"), title=title, goal=goal, created_at=now, updated_at=now)

    def add_task(self, title: str, detail: str = "", assignee: str = "") -> ResearchTask:
        t = ResearchTask(id=new_id("task_"), title=title, detail=detail, assignee=assignee, created_at=time.time())
        self.tasks.append(t)
        self.updated_at = time.time()
        return t

    def add_hypothesis(self, statement: str) -> Hypothesis:
        h = Hypothesis(id=new_id("hyp_"), statement=statement, created_at=time.time())
        self.hypotheses.append(h)
        self.updated_at = time.time()
        return h


class GraphNode(BaseModel):
    id: str
    kind: str  # hypothesis|equation|definition|experiment|result|source|code|question
    label: str
    payload: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    src: str
    dst: str
    relation: str  # supports|refutes|derives|uses|cites|answers


class ResearchGraph(BaseModel):
    nodes: dict[str, GraphNode] = Field(default_factory=dict)
    edges: list[GraphEdge] = Field(default_factory=list)

    def add_node(self, kind: str, label: str, payload: dict[str, Any] | None = None) -> GraphNode:
        n = GraphNode(id=new_id("n_"), kind=kind, label=label, payload=payload or {})
        self.nodes[n.id] = n
        return n

    def link(self, src: str, dst: str, relation: str) -> None:
        self.edges.append(GraphEdge(src=src, dst=dst, relation=relation))
