"""The real providers, reached through a LiteLLM proxy, refuse a made-up key: no secret, no credit (ADR 0101, 0103).

The proxy is the one of the installation, or one started locally with deploy/litellm/config.yaml and a master key
of its own; the test receives its address and the file of the master key as the worker does.
"""

import os
from pathlib import Path

import pytest

from autotrading.adapters.outbound.litellm.model_call import litellm_model_call
from autotrading.adapters.outbound.litellm.model_catalog import litellm_model_catalog
from autotrading.application.agent.errors import ModelKeyRejectedError
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.agent.provider_key import ProviderKey

pytestmark = pytest.mark.providers

MADE_UP_KEY = ProviderKey("K-made-up-key-for-autotrading-tests")
MESSAGES = (ModelMessage(MessageRole.SYSTEM, "Rispondi {}"), ModelMessage(MessageRole.USER, "{}"))


def test_the_catalog_offers_models_of_every_route_and_each_provider_refuses_a_made_up_key() -> None:
    url = os.environ["LITELLM_URL"]
    master_key = Path(os.environ["LITELLM_MASTER_KEY_FILE"]).read_text(encoding="utf-8").strip()
    catalog = litellm_model_catalog(url, master_key).catalog()
    first_model_of = {model.provider: model.name for model in reversed(catalog.models)}
    adapter = litellm_model_call(url, master_key)

    assert {provider.value for provider in first_model_of} == {"anthropic", "deepseek", "openai", "openrouter"}
    for model in first_model_of.values():
        with pytest.raises(ModelKeyRejectedError):
            adapter.call(model, MADE_UP_KEY, {}, MESSAGES)
