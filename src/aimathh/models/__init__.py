"""Model-agnostic provider abstraction.

The harness never depends on one AI vendor. A ``ModelProvider`` exposes
chat + structured-output + (optionally) vision/code capabilities behind a
typed interface, with a capability registry for routing.
"""

from aimathh.models.base import (
    Capability,
    ChatMessage,
    ModelCapabilities,
    ModelRequest,
    ModelResponse,
    ModelProvider,
    ToolCallRequest,
    Usage,
)
from aimathh.models.registry import (
    CapabilityRegistry,
    get_registry,
    register_provider,
    get_provider,
    list_providers,
)
from aimathh.models.mock import MockProvider
from aimathh.models.openai_compat import OpenAICompatProvider
from aimathh.models.anthropic import AnthropicProvider
from aimathh.models.local import LocalOllamaProvider

__all__ = [
    "Capability",
    "ChatMessage",
    "ModelCapabilities",
    "ModelRequest",
    "ModelResponse",
    "ModelProvider",
    "ToolCallRequest",
    "Usage",
    "CapabilityRegistry",
    "get_registry",
    "register_provider",
    "get_provider",
    "list_providers",
    "MockProvider",
    "OpenAICompatProvider",
    "AnthropicProvider",
    "LocalOllamaProvider",
]
