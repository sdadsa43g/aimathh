"""Typed error hierarchy — every subsystem raises HarnessError subclasses."""

from __future__ import annotations


class HarnessError(Exception):
    """Base class for all harness errors."""

    code: str = "harness_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class ToolError(HarnessError):
    code = "tool_error"


class ToolNotFoundError(ToolError):
    code = "tool_not_found"


class ToolTimeoutError(ToolError):
    code = "tool_timeout"


class ToolValidationError(ToolError):
    code = "tool_validation"


class PermissionDeniedError(HarnessError):
    code = "permission_denied"


class SandboxError(HarnessError):
    code = "sandbox_error"


class VerificationError(HarnessError):
    code = "verification_error"


class ModelError(HarnessError):
    code = "model_error"


class BudgetExceededError(HarnessError):
    code = "budget_exceeded"


class NotImplementedSubsystemError(HarnessError):
    """Raised when an explicitly-unimplemented subsystem is invoked.

    The harness must never fake capability: unbuilt integrations raise this
    with a pointer to the roadmap instead of returning plausible output.
    """

    code = "not_implemented_subsystem"
