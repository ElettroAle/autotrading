"""The verifiers of the keys of the providers, one folder each (ADR 0029, ADR 0103), on the same contract."""

import importlib
import logging
import re
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from autotrading.adapters.outbound.anthropic.composition import anthropic_adapters
from autotrading.adapters.outbound.anthropic.key_verifier import AnthropicProviderKeyVerifierAdapter
from autotrading.adapters.outbound.deepseek.composition import deepseek_adapters
from autotrading.adapters.outbound.deepseek.key_verifier import DeepSeekProviderKeyVerifierAdapter
from autotrading.adapters.outbound.openai.composition import openai_adapters
from autotrading.adapters.outbound.openai.key_verifier import OpenAIProviderKeyVerifierAdapter
from autotrading.adapters.outbound.openrouter.composition import openrouter_adapters
from autotrading.adapters.outbound.openrouter.key_verifier import OpenRouterProviderKeyVerifierAdapter
from autotrading.application.agent.errors import ProviderRejectedKeyError, ProviderUnavailableError
from autotrading.application.agent.ports import ProviderKeyVerifierPort
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName

KEY = ProviderKey("K-SECRET-TEST")
PROXY_CONFIGURATION = Path(__file__).parents[3] / "deploy" / "litellm" / "config.yaml"

type Verifier = Callable[[httpx.Client], ProviderKeyVerifierPort]

VERIFIERS: dict[str, Verifier] = {
    "anthropic": AnthropicProviderKeyVerifierAdapter,
    "deepseek": DeepSeekProviderKeyVerifierAdapter,
    "openai": OpenAIProviderKeyVerifierAdapter,
    "openrouter": OpenRouterProviderKeyVerifierAdapter,
}


def verifier_answering(provider: str, status: int, asked: list[httpx.Request] | None = None) -> ProviderKeyVerifierPort:
    def answer(request: httpx.Request) -> httpx.Response:
        if asked is not None:
            asked.append(request)
        return httpx.Response(status, json={"error": {"message": f"bad key {KEY.secret}"}})

    return VERIFIERS[provider](httpx.Client(transport=httpx.MockTransport(answer)))


@pytest.mark.parametrize(
    ("provider", "url", "header", "value"),
    [
        ("anthropic", "https://api.anthropic.com/v1/models", "x-api-key", KEY.secret),
        ("openai", "https://api.openai.com/v1/models", "Authorization", f"Bearer {KEY.secret}"),
        ("deepseek", "https://api.deepseek.com/models", "Authorization", f"Bearer {KEY.secret}"),
        ("openrouter", "https://openrouter.ai/api/v1/key", "Authorization", f"Bearer {KEY.secret}"),
    ],
)
def test_each_provider_is_asked_on_its_free_endpoint_with_the_key(
    provider: str, url: str, header: str, value: str
) -> None:
    asked: list[httpx.Request] = []

    verifier_answering(provider, 200, asked).verify(ProviderName(provider), KEY)

    (request,) = asked
    assert (request.method, str(request.url), request.headers[header]) == ("GET", url, value)


def test_anthropic_is_asked_with_its_api_version() -> None:
    asked: list[httpx.Request] = []

    verifier_answering("anthropic", 200, asked).verify(ProviderName("anthropic"), KEY)

    assert asked[0].headers["anthropic-version"] == "2023-06-01"


@pytest.mark.parametrize("provider", sorted(VERIFIERS))
@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_key_is_rejected_without_the_answer_of_the_provider(provider: str, status: int) -> None:
    with pytest.raises(ProviderRejectedKeyError) as raised:
        verifier_answering(provider, status).verify(ProviderName(provider), KEY)

    assert str(raised.value) == f"chiave rifiutata dal fornitore: {provider}"


@pytest.mark.parametrize("provider", sorted(VERIFIERS))
@pytest.mark.parametrize("status", [429, 500, 503, 302])
def test_any_other_answer_is_a_provider_out_of_reach(provider: str, status: int) -> None:
    with pytest.raises(ProviderUnavailableError, match=rf"^fornitore non raggiungibile, riprovare: {provider}$"):
        verifier_answering(provider, status).verify(ProviderName(provider), KEY)


@pytest.mark.parametrize("provider", sorted(VERIFIERS))
def test_a_network_failure_is_a_provider_out_of_reach_that_never_carries_the_key(
    provider: str, caplog: pytest.LogCaptureFixture
) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        message = f"refused for {dict(request.headers)}"
        raise httpx.ConnectError(message, request=request)

    verifier = VERIFIERS[provider](httpx.Client(transport=httpx.MockTransport(fail)))

    with caplog.at_level(logging.DEBUG), pytest.raises(ProviderUnavailableError) as raised:
        verifier.verify(ProviderName(provider), KEY)

    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__
    assert KEY.secret not in str(raised.value)
    assert KEY.secret not in caplog.text


@pytest.mark.parametrize(
    ("compose", "provider", "verifier"),
    [
        (anthropic_adapters, "anthropic", AnthropicProviderKeyVerifierAdapter),
        (deepseek_adapters, "deepseek", DeepSeekProviderKeyVerifierAdapter),
        (openai_adapters, "openai", OpenAIProviderKeyVerifierAdapter),
        (openrouter_adapters, "openrouter", OpenRouterProviderKeyVerifierAdapter),
    ],
)
def test_each_composition_gives_its_verifier_under_the_name_of_its_provider(
    compose: Callable[[], dict[str, ProviderKeyVerifierPort]], provider: str, verifier: type
) -> None:
    composed = compose()

    assert list(composed) == [provider]
    assert isinstance(composed[provider], verifier)


def test_every_provider_the_proxy_routes_has_a_folder_that_verifies_its_keys() -> None:
    routes = re.findall(r'model_name: "([a-z]+)/\*"', PROXY_CONFIGURATION.read_text(encoding="utf-8"))

    assert routes
    for route in routes:
        composition = importlib.import_module(f"autotrading.adapters.outbound.{route}.composition")
        assert route in getattr(composition, f"{route}_adapters")()
