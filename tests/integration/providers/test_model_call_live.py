"""The real providers, reached through the LiteLLM library, refuse a made-up key: no secret, no credit (ADR 0148).

The library runs in the test process as in the worker: the catalog comes from its model map, the calls go straight to
each enabled provider.
"""

import pytest

from autotrading.adapters.outbound.litellm.composition import litellm_adapters
from autotrading.application.agent.errors import ModelKeyRejectedError
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from tests.support.provider_key import api_key_of

pytestmark = pytest.mark.providers

MADE_UP_KEY = api_key_of("K-made-up-key-for-autotrading-tests")
MESSAGES = (ModelMessage(MessageRole.SYSTEM, "Rispondi {}"), ModelMessage(MessageRole.USER, "{}"))


def test_the_catalog_offers_models_of_every_enabled_provider_and_each_refuses_a_made_up_key() -> None:
    (gateway,) = litellm_adapters().values()
    catalog = gateway.model_catalog().catalog()
    first_model_of = {model.provider: model.name for model in reversed(catalog.models)}

    assert {provider.value for provider in first_model_of} == {"anthropic", "deepseek", "openai"}
    for model in first_model_of.values():
        with pytest.raises(ModelKeyRejectedError):
            gateway.model_call().call(model, MADE_UP_KEY, {}, MESSAGES)
