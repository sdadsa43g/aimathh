"""Self-hosted / local inference via an Ollama-compatible server."""

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


class LocalOllamaProvider(ModelProvider):
    name = "local-ollama"

    def __init__(self, *, base_url: str = "http://localhost:11434", model: str = "", timeout_s: float = 180.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            name=self.model or "local",
            provider="local-ollama",
            context_window=32768,
            capabilities=[Capability.CHAT, Capability.CODE],
            coding_score=0.6,
            reasoning_score=0.6,
            reliability=0.7,
            preferred_tasks=["code", "draft"],
        )

    async def chat(self, request: ModelRequest) -> ModelResponse:
        if not self.model:
            raise ModelError("LOCAL_MODEL is not configured for local-ollama provider")
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})
        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"model": self.model, "messages": messages, "stream": False},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise ModelError(f"Local model call failed: {e}") from e
        text = (data.get("message") or {}).get("content", "")
        return ModelResponse(
            text=text,
            usage=Usage(
                input_tokens=int(data.get("prompt_eval_count", 0)),
                output_tokens=int(data.get("eval_count", 0)),
                latency_s=time.time() - t0,
            ),
            model=self.model,
            provider="local-ollama",
            raw=data,
        )
