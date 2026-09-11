"""Core shared types: config, result objects, provenance, errors."""

from aimathh.core.config import Settings, get_settings
from aimathh.core.errors import (
    HarnessError,
    ToolError,
    ToolNotFoundError,
    ToolTimeoutError,
    PermissionDeniedError,
    SandboxError,
    VerificationError,
    ModelError,
    BudgetExceededError,
)
from aimathh.core.ids import new_id
from aimathh.core.provenance import Provenance, make_provenance
from aimathh.core.types import (
    EvidenceLevel,
    VerificationStatus,
    Assumption,
    Citation,
    ComputationRecord,
    VerificationResult,
    ResearchResult,
    Reproducibility,
    Warning,
)

__all__ = [
    "Settings",
    "get_settings",
    "HarnessError",
    "ToolError",
    "ToolNotFoundError",
    "ToolTimeoutError",
    "PermissionDeniedError",
    "SandboxError",
    "VerificationError",
    "ModelError",
    "BudgetExceededError",
    "new_id",
    "Provenance",
    "make_provenance",
    "EvidenceLevel",
    "VerificationStatus",
    "Assumption",
    "Citation",
    "ComputationRecord",
    "VerificationResult",
    "ResearchResult",
    "Reproducibility",
    "Warning",
]
