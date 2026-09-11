"""Anthropic Messages API provider."""

from __future__ import annotations

import time

import httpx

from aimathh.core.errors import ModelError
from aimathh.models.base import (
    Capability,
    ModelCapabilities,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    Usage,
)


class AnthropicProvider(ModelProvider):
    name = "anthropic"

    def __init__(
        self,
        *,
        base_url: str = "https://api.anthropic.com",
        api_key: str = "",
        model: str = "claude-3-5-sonnet-latest",
        timeout_s: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            name=self.model,
            provider="anthropic",
            context_window=200000,
            capabilities=[Capability.CHAT, Capability.TOOL_USE, Capability.CODE, Capability.REASONING],
            structured_output=False,
            coding_score=0.9,
            reasoning_score=0.9,
            reliability=0.88,
            preferred_tasks=["plan", "code", "proof", "critique"],
        )

    async def chat(self, request: ModelRequest) -> ModelResponse:
        if not self.api_key:
            raise ModelError("ANTHROPIC_API_KEY is not configured")
        messages = [
            {"role": "user" if m.role in ("user", "tool") else "assistant", "content": m.content}
            for m in request.messages
            if m.role != "system"
        ]
        body: dict = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            "messages": messages or [{"role": "user", "content": ""}],
        }
        if request.system:
            body["system"] = request.system
        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise ModelError(f"Anthropic call failed: {e}") from e
        blocks = data.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        usage = data.get("usage") or {}
        return ModelResponse(
            text=text,
            usage=Usage(
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
                latency_s=time.time() - t0,
            ),
            model=self.model,
            provider="anthropic",
            raw=data,
        )
