"""OpenAI-compatible chat provider (OpenAI, vLLM, Together, OpenRouter, ...)."""

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
    ToolCallRequest,
    Usage,
)


class OpenAICompatProvider(ModelProvider):
    name = "openai-compat"

    def __init__(
        self,
        *,
        base_url: str = "https://api.openai.com/v1",
        api_key: str = "",
        model: str = "gpt-4o-mini",
        context_window: int = 128000,
        timeout_s: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.context_window = context_window
        self.timeout_s = timeout_s

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            name=self.model,
            provider="openai-compat",
            context_window=self.context_window,
            capabilities=[
                Capability.CHAT,
                Capability.STRUCTURED_OUTPUT,
                Capability.TOOL_USE,
                Capability.CODE,
                Capability.REASONING,
            ],
            structured_output=True,
            coding_score=0.85,
            reasoning_score=0.8,
            reliability=0.85,
            preferred_tasks=["plan", "code", "research", "critique"],
        )

    async def chat(self, request: ModelRequest) -> ModelResponse:
        if not self.api_key:
            raise ModelError("OPENAI_API_KEY (or compatible key) is not configured")
        messages: list[dict] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        for m in request.messages:
            messages.append({"role": m.role, "content": m.content})
        body: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.tools:
            body["tools"] = request.tools
        if request.response_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "result", "schema": request.response_schema},
            }
        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise ModelError(f"OpenAI-compatible call failed: {e}") from e
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        tool_calls: list[ToolCallRequest] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            import json as _json

            try:
                args = _json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {"_raw": fn.get("arguments")}
            tool_calls.append(ToolCallRequest(id=tc.get("id", ""), name=fn.get("name", ""), arguments=args))
        usage = data.get("usage") or {}
        return ModelResponse(
            text=msg.get("content") or "",
            tool_calls=tool_calls,
            usage=Usage(
                input_tokens=int(usage.get("prompt_tokens", 0)),
                output_tokens=int(usage.get("completion_tokens", 0)),
                latency_s=time.time() - t0,
            ),
            model=self.model,
            provider="openai-compat",
            raw=data,
        )
