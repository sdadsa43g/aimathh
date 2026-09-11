"""Model provider abstraction + registry routing."""

import pytest

from aimathh.models import MockProvider, get_provider, list_providers, register_provider
from aimathh.models.base import Capability, ChatMessage, ModelRequest


@pytest.fixture()
def _mock():
    p = MockProvider()
    if "mock" not in list_providers():
        register_provider(p)
    return p


async def test_mock_chat(_mock):
    resp = await _mock.chat(ModelRequest(messages=[ChatMessage(role="user", content="hello")]))
    assert resp.text and resp.provider == "mock"


async def test_mock_structured(_mock):
    resp = await _mock.complete_structured(
        ModelRequest(messages=[ChatMessage(role="user", content="plan")]), {"type": "object"})
    assert isinstance(resp.structured, dict)
    assert "steps" in resp.structured


async def test_registry_routing(_mock):
    assert "mock" in list_providers()
    assert get_provider("mock").supports(Capability.CHAT)


async def test_openai_requires_key():
    from aimathh.core.errors import ModelError
    from aimathh.models import OpenAICompatProvider

    p = OpenAICompatProvider(api_key="")
    with pytest.raises(ModelError):
        await p.chat(ModelRequest(messages=[ChatMessage(content="hi")]))
