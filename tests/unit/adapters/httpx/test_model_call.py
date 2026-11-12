"""The model call adapter against the four providers, served in memory in the shapes they answer with."""

import json
from collections.abc import Callable
from decimal import Decimal

import httpx
import pytest

from autotrading.adapters.outbound.httpx.model_call import HttpxModelCallAdapter
from autotrading.application.agent.errors import (
    ModelCreditExhaustedError,
    ModelKeyRejectedError,
    ModelUnavailableError,
    UnsupportedProviderError,
)
from autotrading.application.agent.ports import ModelReply
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.agent.model_parameter import ParameterValue
from autotrading.domain.agent.model_usage import ModelUsage
from autotrading.domain.agent.provider_key import ProviderKey

KEY = ProviderKey("K-FAKE-MODEL-KEY")
MESSAGES = (ModelMessage(MessageRole.SYSTEM, "regole"), ModelMessage(MessageRole.USER, '{"ora_corrente": "10:30"}'))
SETTINGS: dict[str, ParameterValue] = {
    "temperature": Decimal("0.7"),
    "max_tokens": Decimal(2048),
    "reasoning_effort": "alto",
}
ANSWER = '{"decisioni": []}'
TIMED_OUT, REFUSED = "timed out", "connection refused"
CHAT_USAGE: dict[str, object] = {"prompt_tokens": 2000, "completion_tokens": 500}
CHAT_REPLY: dict[str, object] = {
    "choices": [{"message": {"role": "assistant", "content": ANSWER}}],
    "usage": CHAT_USAGE,
}
ANTHROPIC_REPLY = {
    "content": [{"type": "thinking", "thinking": "..."}, {"type": "text", "text": ANSWER}],
    "usage": {"input_tokens": 2000, "output_tokens": 500},
}

type Answer = Callable[[httpx.Request], httpx.Response]


class Provider:
    """A provider in memory that records the requests it receives."""

    def __init__(self, status: int = 200, body: object = None, text: str | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self._status, self._body, self._text = status, body, text

    def answer(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._text is not None:
            return httpx.Response(self._status, text=self._text)
        return httpx.Response(self._status, json=self._body)

    @property
    def sent(self) -> dict[str, object]:
        body: dict[str, object] = json.loads(self.requests[0].content)
        return body


def call(provider: Provider, model: str, settings: dict[str, ParameterValue] | None = None) -> ModelReply:
    adapter = HttpxModelCallAdapter(httpx.Client(transport=httpx.MockTransport(provider.answer)))
    return adapter.call(model, KEY, SETTINGS if settings is None else settings, MESSAGES)


def failing(answer: Answer, model: str = "openrouter/deepseek/deepseek-chat") -> None:
    HttpxModelCallAdapter(httpx.Client(transport=httpx.MockTransport(answer))).call(model, KEY, {}, MESSAGES)


def test_openrouter_gets_the_routed_model_and_reports_the_cost() -> None:
    provider = Provider(body={**CHAT_REPLY, "usage": {**CHAT_USAGE, "cost": 0.0031}})

    reply = call(provider, "openrouter/deepseek/deepseek-chat")

    assert reply == ModelReply(ANSWER, ModelUsage(2000, 500, Decimal("0.0031")))
    request = provider.requests[0]
    assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer K-FAKE-MODEL-KEY"
    assert provider.sent == {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "system", "content": "regole"}, {"role": "user", "content": '{"ora_corrente": "10:30"}'}],
        "max_tokens": 2048,
        "temperature": 0.7,
        "reasoning": {"effort": "high"},
    }


def test_openai_gets_a_json_answer_and_its_own_names_for_the_parameters() -> None:
    provider = Provider(body=CHAT_REPLY)

    reply = call(provider, "openai/gpt-4.1-mini")

    assert reply == ModelReply(ANSWER, ModelUsage(2000, 500, None))
    assert str(provider.requests[0].url) == "https://api.openai.com/v1/chat/completions"
    assert provider.sent == {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "system", "content": "regole"}, {"role": "user", "content": '{"ora_corrente": "10:30"}'}],
        "max_completion_tokens": 2048,
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
        "reasoning_effort": "high",
    }


def test_deepseek_gets_a_json_answer_without_reasoning_effort() -> None:
    provider = Provider(body=CHAT_REPLY)

    call(provider, "deepseek/deepseek-chat")

    assert str(provider.requests[0].url) == "https://api.deepseek.com/chat/completions"
    assert provider.requests[0].headers["Authorization"] == "Bearer K-FAKE-MODEL-KEY"
    assert provider.sent == {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": "regole"}, {"role": "user", "content": '{"ora_corrente": "10:30"}'}],
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }


def test_anthropic_gets_the_system_apart_and_answers_with_its_text_blocks() -> None:
    provider = Provider(body=ANTHROPIC_REPLY)

    reply = call(provider, "anthropic/claude-sonnet-5-5")

    assert reply == ModelReply(ANSWER, ModelUsage(2000, 500, None))
    request = provider.requests[0]
    assert str(request.url) == "https://api.anthropic.com/v1/messages"
    assert (request.headers["x-api-key"], request.headers["anthropic-version"]) == ("K-FAKE-MODEL-KEY", "2023-06-01")
    assert "Authorization" not in request.headers
    assert provider.sent == {
        "model": "claude-sonnet-5-5",
        "max_tokens": 2048,
        "system": "regole",
        "messages": [{"role": "user", "content": '{"ora_corrente": "10:30"}'}],
        "temperature": 0.7,
        "output_config": {"effort": "high"},
    }


@pytest.mark.parametrize(("effort", "expected"), [("basso", "low"), ("medio", "medium"), ("alto", "high")])
def test_the_reasoning_levels_become_the_names_of_the_provider(effort: str, expected: str) -> None:
    provider = Provider(body=CHAT_REPLY)

    call(provider, "openai/o4-mini", {"reasoning_effort": effort})

    assert provider.sent["reasoning_effort"] == expected


@pytest.mark.parametrize("model", ["openai/gpt", "deepseek/deepseek-chat", "openrouter/x/y", "anthropic/claude"])
def test_without_settings_the_defaults_of_the_provider_apply(model: str) -> None:
    provider = Provider(body=ANTHROPIC_REPLY if model.startswith("anthropic") else CHAT_REPLY)

    call(provider, model, {})

    sent = provider.sent
    assert "temperature" not in sent
    assert "reasoning_effort" not in sent
    assert "reasoning" not in sent
    assert "output_config" not in sent
    assert sent.get("max_tokens", sent.get("max_completion_tokens")) == 4096


def test_a_provider_outside_the_catalog_is_not_supported() -> None:
    with pytest.raises(UnsupportedProviderError, match=r"^fornitore non supportato: mistral$"):
        call(Provider(body=CHAT_REPLY), "mistral/large")


@pytest.mark.parametrize("status", [401, 403])
@pytest.mark.parametrize("model", ["openrouter/x/y", "anthropic/claude", "openai/gpt", "deepseek/deepseek-chat"])
def test_a_rejected_key_is_a_permanent_error(status: int, model: str) -> None:
    provider = Provider(status, {"error": {"message": "Incorrect API key provided: K-FAKE-MODEL-KEY"}})

    with pytest.raises(ModelKeyRejectedError) as raised:
        call(provider, model)

    provider_name = model.partition("/")[0]
    assert str(raised.value) == f"chiave del fornitore non valida: {provider_name}"
    assert raised.value.permanent
    assert "K-FAKE" not in str(raised.value)


@pytest.mark.parametrize("model", ["openrouter/x/y", "anthropic/claude", "deepseek/deepseek-chat"])
def test_payment_required_is_an_exhausted_credit(model: str) -> None:
    with pytest.raises(ModelCreditExhaustedError) as raised:
        call(Provider(402, {"error": {"code": 402, "message": "Insufficient credits"}}), model)

    assert str(raised.value) == f"credito esaurito presso {model.partition('/')[0]}"
    assert raised.value.permanent


def test_an_exhausted_openai_quota_is_an_exhausted_credit() -> None:
    body = {
        "error": {
            "message": "You exceeded your current quota",
            "type": "insufficient_quota",
            "code": "insufficient_quota",
        }
    }

    with pytest.raises(ModelCreditExhaustedError, match=r"^credito esaurito presso openai$"):
        call(Provider(429, body), "openai/gpt")


def test_a_rate_limit_is_transient() -> None:
    body = {"error": {"message": "Rate limit reached", "code": "rate_limit_exceeded"}}

    with pytest.raises(
        ModelUnavailableError, match=r"^fornitore IA non raggiungibile: openai: 429 Rate limit reached$"
    ) as raised:
        call(Provider(429, body), "openai/gpt")

    assert not raised.value.permanent
    assert raised.value.original == "429 Rate limit reached"


@pytest.mark.parametrize(
    ("status", "body", "text", "original"),
    [
        (
            529,
            {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}},
            None,
            "529 Overloaded",
        ),
        (502, None, "<html>\n  Bad   gateway\n</html>", "502 <html> Bad gateway </html>"),
        (500, {"error": "boom"}, None, '500 {"error":"boom"}'),
        (503, ["unavailable"], None, '503 ["unavailable"]'),
        (400, {"error": {"message": 42}}, None, '400 {"error":{"message":42}}'),
    ],
)
def test_other_refusals_are_transient_with_the_original_message(
    status: int, body: object, text: str | None, original: str
) -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(Provider(status, body, text), "anthropic/claude")

    assert raised.value.original == original


def test_a_long_original_message_is_cut() -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(Provider(500, {"error": {"message": "x" * 1000}}), "openai/gpt")

    assert raised.value.original == "500 " + "x" * 300


def test_the_key_never_travels_in_a_transient_error() -> None:
    body = {"error": {"message": "upstream rejected header Bearer K-FAKE-MODEL-KEY"}}

    with pytest.raises(ModelUnavailableError) as raised:
        call(Provider(500, body), "openrouter/x/y")

    assert "K-FAKE-MODEL-KEY" not in str(raised.value)


def test_a_timeout_is_transient() -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(TIMED_OUT, request=request)

    with pytest.raises(
        ModelUnavailableError, match=r"^fornitore IA non raggiungibile: openrouter: tempo di risposta scaduto$"
    ):
        failing(slow)


def test_an_unreachable_provider_is_transient() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    with pytest.raises(
        ModelUnavailableError, match=r"^fornitore IA non raggiungibile: openrouter: ConnectError$"
    ) as raised:
        failing(refuse)

    assert raised.value.__cause__ is None


@pytest.mark.parametrize(
    ("model", "body"),
    [
        ("openai/gpt", {"choices": [], "usage": {"prompt_tokens": 1, "completion_tokens": 1}}),
        ("openai/gpt", {"choices": [{"message": {"content": "x"}}]}),
        (
            "openai/gpt",
            {"choices": [{"message": {"content": "x"}}], "usage": {"prompt_tokens": "many", "completion_tokens": 1}},
        ),
        ("openrouter/x/y", {**CHAT_REPLY, "usage": {**CHAT_USAGE, "cost": "free"}}),
        ("anthropic/claude", {"content": [{"type": "text"}], "usage": {"input_tokens": 1, "output_tokens": 1}}),
        ("anthropic/claude", {"content": None, "usage": {"input_tokens": 1, "output_tokens": 1}}),
        ("anthropic/claude", {"content": [], "usage": {"input_tokens": -1, "output_tokens": 1}}),
    ],
)
def test_an_answer_in_another_shape_is_transient(model: str, body: object) -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(Provider(200, body), model)

    assert raised.value.original == "risposta del fornitore inattesa"


def test_an_answer_that_is_not_json_is_transient() -> None:
    with pytest.raises(ModelUnavailableError, match=r"risposta del fornitore inattesa$"):
        call(Provider(200, text="<html>ok</html>"), "openai/gpt")
