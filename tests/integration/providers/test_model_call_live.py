"""The real providers refuse a made-up key on the endpoints the model call uses: no secret, no credit (ADR 0039)."""

import httpx
import pytest

from autotrading.adapters.outbound.httpx.model_call import HttpxModelCallAdapter
from autotrading.adapters.outbound.json.model_catalog import load_model_catalog
from autotrading.application.agent.errors import ModelKeyRejectedError
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.agent.provider_key import ProviderKey

pytestmark = pytest.mark.providers

MADE_UP_KEY = ProviderKey("K-made-up-key-for-autotrading-tests")
MESSAGES = (ModelMessage(MessageRole.SYSTEM, "Rispondi {}"), ModelMessage(MessageRole.USER, "{}"))


@pytest.mark.parametrize("model", [model.name for model in load_model_catalog().models])
def test_the_provider_refuses_a_made_up_key_for_every_model_of_the_catalog(model: str) -> None:
    with httpx.Client() as client, pytest.raises(ModelKeyRejectedError):
        HttpxModelCallAdapter(client).call(model, MADE_UP_KEY, {}, MESSAGES)
