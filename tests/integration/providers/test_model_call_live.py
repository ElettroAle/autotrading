"""The real providers, reached through a LiteLLM proxy, refuse a made-up key: no secret, no credit (ADR 0101).

The proxy is the one of the installation, or one started locally with deploy/litellm/config.yaml and a master key
of its own; the test receives its address and the file of the master key as the worker does.
"""

import os
from pathlib import Path

import pytest

from autotrading.adapters.outbound.json.model_catalog import load_model_catalog
from autotrading.adapters.outbound.litellm.model_call import litellm_model_call
from autotrading.application.agent.errors import ModelKeyRejectedError
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.agent.provider_key import ProviderKey

pytestmark = pytest.mark.providers

MADE_UP_KEY = ProviderKey("K-made-up-key-for-autotrading-tests")
MESSAGES = (ModelMessage(MessageRole.SYSTEM, "Rispondi {}"), ModelMessage(MessageRole.USER, "{}"))


@pytest.mark.parametrize("model", [model.name for model in load_model_catalog().models])
def test_the_provider_refuses_a_made_up_key_for_every_model_of_the_catalog(model: str) -> None:
    master_key = Path(os.environ["LITELLM_MASTER_KEY_FILE"]).read_text(encoding="utf-8").strip()
    adapter = litellm_model_call(os.environ["LITELLM_URL"], master_key)

    with pytest.raises(ModelKeyRejectedError):
        adapter.call(model, MADE_UP_KEY, {}, MESSAGES)
