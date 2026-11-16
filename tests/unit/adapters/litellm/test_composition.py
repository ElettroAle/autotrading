"""The gateway of the LiteLLM library inside the worker, with no address and no key of the platform (ADR 0148)."""

import litellm
import pytest

from autotrading.adapters.outbound.litellm.composition import litellm_adapters
from autotrading.adapters.outbound.litellm.configuration import _LiteLlmSettings
from autotrading.adapters.outbound.litellm.model_gateway import LiteLlmModelGatewayAdapter
from autotrading.domain.agent.answer_format import DECISIONS_FORMAT
from autotrading.domain.agent.provider_name import ProviderName
from tests.support.provider_key import api_key_of

ENABLED = ("anthropic", "deepseek", "openai")


def test_the_gateway_of_the_library_is_offered_by_its_name() -> None:
    gateways = litellm_adapters()

    assert list(gateways) == ["litellm"]
    assert isinstance(gateways["litellm"], LiteLlmModelGatewayAdapter)


def test_the_catalog_offers_the_chat_models_the_library_knows_for_the_enabled_providers() -> None:
    (gateway,) = litellm_adapters().values()

    catalog = gateway.model_catalog().catalog()

    assert catalog.providers == tuple(ProviderName(provider) for provider in ENABLED)
    assert len(catalog.models) > len(ENABLED)


def test_the_enabled_providers_and_the_wait_are_settings_of_the_adapter() -> None:
    settings = _LiteLlmSettings()

    assert (settings.providers, settings.timeout_seconds) == (frozenset(ENABLED), 120.0)


def test_messages_and_answers_never_reach_the_logs_and_nobody_is_called_back() -> None:
    litellm_adapters()

    assert litellm.turn_off_message_logging is True
    assert (litellm.callbacks, litellm.success_callback, litellm.failure_callback) == ([], [], [])


def test_the_call_asks_the_strict_format_of_a_model_the_library_declares_able(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR risposta-del-modello-con-schema-rigido: the capability is the one of the map of the library."""
    requests: list[dict[str, object]] = []

    def completion(**request: object) -> litellm.ModelResponse:
        requests.append(request)
        choices = [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "{}"}}]
        usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
        return litellm.ModelResponse(model="m", choices=choices, usage=usage)

    monkeypatch.setattr(litellm, "completion", completion)
    (gateway,) = litellm_adapters().values()

    for model in ("openai/gpt-4.1-mini", "openai/not-a-model-of-the-map"):
        gateway.model_call().call(model, api_key_of("K-FAKE"), {}, (), DECISIONS_FORMAT)

    assert [request["response_format"]["type"] for request in requests] == ["json_schema", "json_object"]  # type: ignore[index]  # a mapping of the request
