"""Deterministic mock provider for tests, demos and offline development."""

from __future__ import annotations

import json

from aimathh.models.base import (
    Capability,
    ModelCapabilities,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    Usage,
)


class MockProvider(ModelProvider):
    """Produces a fixed, inspectable plan instead of calling any API."""

    name = "mock"

    def __init__(self, model: str = "mock-plan-0.1") -> None:
        self._model = model

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            name=self._model,
            provider="mock",
            context_window=32768,
            capabilities=[Capability.CHAT, Capability.STRUCTURED_OUTPUT, Capability.TOOL_USE, Capability.CODE],
            structured_output=True,
            coding_score=0.4,
            reasoning_score=0.4,
            reliability=1.0,
            preferred_tasks=["test", "demo", "plan"],
        )

    async def chat(self, request: ModelRequest) -> ModelResponse:
        user_text = "\n".join(m.content for m in request.messages if m.role == "user")[-2000:]
        plan = {
            "understanding": f"Mock plan for request ({len(user_text)} chars).",
            "steps": [
                {"kind": "formulate", "detail": "Restate problem with assumptions."},
                {"kind": "compute", "detail": "Run symbolic + numeric tools."},
                {"kind": "verify", "detail": "Cross-check with independent method."},
            ],
            "wanted_tools": ["python_exec", "symbolic", "numeric"],
        }
        text = "MOCK PLAN:\n" + json.dumps(plan, indent=2)
        if request.response_schema is not None:
            return ModelResponse(
                text=text, structured=plan, usage=Usage(), model=self._model, provider="mock"
            )
        return ModelResponse(text=text, usage=Usage(), model=self._model, provider="mock")
