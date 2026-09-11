"""Structured result system — the harness never returns plain text only.

Every significant computation produces a :class:`ResearchResult` carrying
equations, assumptions, computations, verification, confidence, evidence,
artifacts, citations, warnings and reproducibility metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceLevel(str, Enum):
    """Epistemic status ladder. Never promote a result above its evidence."""

    PROVEN = "proven"  # formal proof / machine-checked
    VERIFIED_COMPUTATION = "verified_computation"  # independent checks agree
    NUMERICALLY_CONFIRMED = "numerically_confirmed"  # strong numeric evidence
    STRONGLY_SUPPORTED = "strongly_supported"  # multiple weak lines agree
    HEURISTIC = "heuristic"  # plausible, unchecked
    HYPOTHESIS = "hypothesis"  # proposed, untested
    UNVERIFIED = "unverified"  # default until checks run
    REFUTED = "refuted"  # counterexample / failed check


class VerificationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"
    NOT_RUN = "not_run"
    ERROR = "error"


class Assumption(BaseModel):
    id: str = ""
    statement: str
    kind: Literal["axiom", "model", "approximation", "boundary", "domain", "other"] = "other"
    justified: bool = False
    source: str = ""


class Citation(BaseModel):
    id: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    venue: str = ""
    year: int | None = None
    doi: str = ""
    arxiv_id: str = ""
    url: str = ""
    retrieved_at: datetime | None = None
    claim: str = ""  # which claim this source supports
    kind: Literal[
        "paper_claim",
        "experimental_evidence",
        "theoretical_derivation",
        "model_assumption",
        "reference_data",
        "other",
    ] = "other"
    verified_retrieved: bool = False  # True only if actually fetched


class ComputationRecord(BaseModel):
    id: str = ""
    tool: str
    method: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    output_summary: str = ""
    output: Any = None
    precision: str = ""
    tolerance: float | None = None
    seed: int | None = None
    duration_s: float = 0.0
    provenance_id: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CheckOutcome(BaseModel):
    name: str
    status: VerificationStatus = VerificationStatus.NOT_RUN
    detail: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    duration_s: float = 0.0


class VerificationResult(BaseModel):
    """Structured verification verdict with per-check evidence."""

    status: VerificationStatus = VerificationStatus.NOT_RUN
    evidence_level: EvidenceLevel = EvidenceLevel.UNVERIFIED
    methods: list[str] = Field(default_factory=list)
    checks: list[CheckOutcome] = Field(default_factory=list)
    symbolic_check: CheckOutcome | None = None
    numerical_check: CheckOutcome | None = None
    dimensional_check: CheckOutcome | None = None
    independent_check: CheckOutcome | None = None
    precision: str = ""
    tolerance: float | None = None
    counterexamples: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    discrepancy_report: str = ""
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def check(self, name: str) -> CheckOutcome | None:
        for c in self.checks:
            if c.name == name:
                return c
        return None

    def passed(self) -> bool:
        return self.status == VerificationStatus.PASSED


class Warning(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "critical"] = "warning"


class Reproducibility(BaseModel):
    experiment_id: str = ""
    run_id: str = ""
    seed: int | None = None
    python_version: str = ""
    dependencies: dict[str, str] = Field(default_factory=dict)
    environment_snapshot: dict[str, Any] = Field(default_factory=dict)
    parameter_manifest: dict[str, Any] = Field(default_factory=dict)
    replay_instructions: str = ""


class ArtifactRef(BaseModel):
    artifact_id: str
    kind: str = ""
    path: str = ""
    mime: str = ""
    description: str = ""


class ResearchResult(BaseModel):
    """Top-level structured answer object."""

    id: str = ""
    title: str = ""
    answer: str  # human-readable summary (markdown allowed)
    equations: list[str] = Field(default_factory=list)  # LaTeX strings
    assumptions: list[Assumption] = Field(default_factory=list)
    computations: list[ComputationRecord] = Field(default_factory=list)
    verification: VerificationResult = Field(default_factory=VerificationResult)
    confidence: float = 0.0  # 0..1 calibrated against verification, not vibes
    evidence: list[str] = Field(default_factory=list)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    warnings: list[Warning] = Field(default_factory=list)
    reproducibility: Reproducibility = Field(default_factory=Reproducibility)
    open_questions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def evidence_level(self) -> EvidenceLevel:
        return self.verification.evidence_level

    def label(self) -> str:
        """Short verdict label for UI badges, e.g. 'VERIFIED' / 'UNVERIFIED'."""
        mapping = {
            EvidenceLevel.PROVEN: "PROVEN",
            EvidenceLevel.VERIFIED_COMPUTATION: "VERIFIED",
            EvidenceLevel.NUMERICALLY_CONFIRMED: "NUMERICALLY CONFIRMED",
            EvidenceLevel.STRONGLY_SUPPORTED: "SUPPORTED",
            EvidenceLevel.HEURISTIC: "HEURISTIC",
            EvidenceLevel.HYPOTHESIS: "HYPOTHESIS",
            EvidenceLevel.UNVERIFIED: "UNVERIFIED",
            EvidenceLevel.REFUTED: "REFUTED",
        }
        return mapping[self.evidence_level]
