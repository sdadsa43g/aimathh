"""Provider interfaces, message types and capability descriptors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Capability(str, Enum):
    CHAT = "chat"
    STRUCTURED_OUTPUT = "structured_output"
    TOOL_USE = "tool_use"
    VISION = "vision"
    CODE = "code"
    LONG_CONTEXT = "long_context"
    REASONING = "reasoning"


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: str = ""
    name: str = ""
    tool_call_id: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class ToolCallRequest(BaseModel):
    id: str = ""
    name: str = ""
    arguments: dict[str, Any] = Field(default_factory=dict)


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    cost_usd: float | None = None


class ModelRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    system: str = ""
    max_tokens: int = 4096
    temperature: float = 0.2
    response_schema: dict[str, Any] | None = None  # JSON schema for structured output
    tools: list[dict[str, Any]] = Field(default_factory=list)  # OpenAI-style tool defs
    stop: list[str] = Field(default_factory=list)
    seed: int | None = None


class ModelResponse(BaseModel):
    text: str = ""
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    structured: Any = None
    usage: Usage = Field(default_factory=Usage)
    model: str = ""
    provider: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class ModelCapabilities(BaseModel):
    name: str
    provider: str
    context_window: int = 8192
    capabilities: list[Capability] = Field(default_factory=list)
    structured_output: bool = False
    vision: bool = False
    coding_score: float = 0.5  # 0..1 heuristic for routing
    reasoning_score: float = 0.5
    latency_ms_p50: float = 1500.0
    cost_per_1k_in: float = 0.0
    cost_per_1k_out: float = 0.0
    reliability: float = 0.8
    preferred_tasks: list[str] = Field(default_factory=list)


class ModelProvider(ABC):
    """Abstract model backend. Implementations must be side-effect free
    except for the billable inference call itself."""

    name: str = "base"

    @abstractmethod
    async def chat(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError

    @abstractmethod
    def capabilities(self) -> ModelCapabilities:
        raise NotImplementedError

    def supports(self, cap: Capability) -> bool:
        return cap in self.capabilities().capabilities

    async def complete_structured(
        self, request: ModelRequest, schema: dict[str, Any]
    ) -> ModelResponse:
        """Request JSON-schema-constrained output; default falls back to chat."""
        request.response_schema = schema
        return await self.chat(request)
