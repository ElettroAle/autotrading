"""OpenRouter for real: its public list makes the catalog, and it refuses a made-up key. No credit spent (ADR 0109)."""

import pytest

from autotrading.adapters.outbound.openrouter.composition import openrouter_adapters
from autotrading.application.agent.errors import ModelKeyRejectedError
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.agent.provider_key import ProviderKey

pytestmark = pytest.mark.providers

MADE_UP_KEY = ProviderKey("sk-or-v1-made-up-key-for-autotrading-tests")
MESSAGES = (ModelMessage(MessageRole.SYSTEM, "Rispondi {}"), ModelMessage(MessageRole.USER, "{}"))
SOME_MODELS = 100


def test_the_public_list_makes_the_catalog_and_a_made_up_key_is_refused() -> None:
    gateway = openrouter_adapters()

    catalog = gateway.model_catalog().catalog()
    free = [model for model in catalog.models if model.name.endswith(":free")]

    assert len(catalog.models) > SOME_MODELS
    assert free
    with pytest.raises(ModelKeyRejectedError):
        gateway.model_call().call(free[0].name, MADE_UP_KEY, {}, MESSAGES)
