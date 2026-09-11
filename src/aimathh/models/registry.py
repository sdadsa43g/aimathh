"""Provider registry + capability routing."""

from __future__ import annotations

from aimathh.core.errors import ModelError
from aimathh.models.base import Capability, ModelProvider


class CapabilityRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: ModelProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> ModelProvider:
        if name not in self._providers:
            raise ModelError(f"Unknown model provider '{name}'", details={"available": list(self._providers)})
        return self._providers[name]

    def list(self) -> list[str]:
        return sorted(self._providers)

    def route(self, *, needs: list[Capability] | None = None, task: str = "") -> ModelProvider:
        """Pick the best provider for a task. Deterministic, no hidden magic."""
        needs = needs or []
        candidates = list(self._providers.values())
        if not candidates:
            raise ModelError("No model providers registered")
        scored: list[tuple[float, ModelProvider]] = []
        for p in candidates:
            caps = p.capabilities()
            if any(n not in caps.capabilities for n in needs):
                continue
            score = caps.reliability + caps.reasoning_score
            if task and task in caps.preferred_tasks:
                score += 0.5
            scored.append((score, p))
        if not scored:
            # fall back to any provider rather than failing hard
            return candidates[0]
        scored.sort(key=lambda t: t[0], reverse=True)
        return scored[0][1]


_registry = CapabilityRegistry()


def get_registry() -> CapabilityRegistry:
    return _registry


def register_provider(provider: ModelProvider) -> None:
    _registry.register(provider)


def get_provider(name: str) -> ModelProvider:
    return _registry.get(name)


def list_providers() -> list[str]:
    return _registry.list()
