"""Verification architecture (Levels 0-5) + quality gate + counterexamples."""

from aimathh.verification.engine import (
    VerificationEngine,
    QualityGate,
    DiscrepancyReport,
    get_verification_engine,
)
from aimathh.verification.counterexample import CounterexampleEngine, get_counterexample_engine
from aimathh.verification import formal

__all__ = [
    "VerificationEngine",
    "QualityGate",
    "DiscrepancyReport",
    "get_verification_engine",
    "CounterexampleEngine",
    "get_counterexample_engine",
    "formal",
]
