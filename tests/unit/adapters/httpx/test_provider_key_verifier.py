import logging

import httpx
import pytest

from autotrading.adapters.outbound.httpx.provider_key_verifier import KEY_CHECKS, HttpxProviderKeyVerifierAdapter
from autotrading.application.agent.errors import (
    ProviderNotVerifiableError,
    ProviderRejectedKeyError,
    ProviderUnavailableError,
)
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName

KEY = ProviderKey("K-SECRET-TEST")


def verifier_answering(status: int, asked: list[httpx.Request] | None = None) -> HttpxProviderKeyVerifierAdapter:
    def answer(request: httpx.Request) -> httpx.Response:
        if asked is not None:
            asked.append(request)
        return httpx.Response(status, json={"error": {"message": f"bad key {KEY.secret}"}})

    return HttpxProviderKeyVerifierAdapter(httpx.Client(transport=httpx.MockTransport(answer)))


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

    verifier_answering(200, asked).verify(ProviderName(provider), KEY)

    (request,) = asked
    assert (request.method, str(request.url), request.headers[header]) == ("GET", url, value)


def test_anthropic_is_asked_with_its_api_version() -> None:
    asked: list[httpx.Request] = []

    verifier_answering(200, asked).verify(ProviderName("anthropic"), KEY)

    assert asked[0].headers["anthropic-version"] == "2023-06-01"


@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_key_is_rejected_without_the_answer_of_the_provider(status: int) -> None:
    with pytest.raises(ProviderRejectedKeyError) as raised:
        verifier_answering(status).verify(ProviderName("openai"), KEY)

    assert str(raised.value) == "chiave rifiutata dal fornitore: openai"


@pytest.mark.parametrize("status", [429, 500, 503, 302])
def test_any_other_answer_is_a_provider_out_of_reach(status: int) -> None:
    with pytest.raises(ProviderUnavailableError, match=r"^fornitore non raggiungibile, riprovare: deepseek$"):
        verifier_answering(status).verify(ProviderName("deepseek"), KEY)


def test_a_network_failure_is_a_provider_out_of_reach_that_never_carries_the_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        message = f"refused for {request.headers['Authorization']}"
        raise httpx.ConnectError(message, request=request)

    verifier = HttpxProviderKeyVerifierAdapter(httpx.Client(transport=httpx.MockTransport(fail)))

    with caplog.at_level(logging.DEBUG), pytest.raises(ProviderUnavailableError) as raised:
        verifier.verify(ProviderName("openrouter"), KEY)

    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__
    assert KEY.secret not in str(raised.value)
    assert KEY.secret not in caplog.text


def test_a_provider_without_a_check_cannot_be_verified() -> None:
    with pytest.raises(ProviderNotVerifiableError) as raised:
        verifier_answering(200).verify(ProviderName("mistral"), KEY)

    assert raised.value.status_code == 500


def test_the_checks_cover_the_providers_the_adr_names() -> None:
    assert sorted(KEY_CHECKS) == ["anthropic", "deepseek", "openai", "openrouter"]
