"""The model call on the API of OpenRouter, served in memory in the shapes OpenRouter answers with (ADR 0109)."""

import json
from decimal import Decimal

import httpx
import pytest

from autotrading.adapters.outbound.openrouter.model_call import OpenRouterModelCallAdapter
from autotrading.application.agent.errors import (
    ModelCreditExhaustedError,
    ModelKeyRejectedError,
    ModelUnavailableError,
)
from autotrading.application.agent.ports import ModelReply
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.agent.answer_format import AnswerFormat
from autotrading.domain.agent.model_parameter import ParameterValue
from autotrading.domain.agent.model_usage import ModelUsage
from tests.support.provider_key import api_key_of

KEY = api_key_of("sk-or-FAKE-MODEL-KEY")
MODEL = "openrouter/deepseek/deepseek-chat"
MESSAGES = (ModelMessage(MessageRole.SYSTEM, "regole"), ModelMessage(MessageRole.USER, '{"ora": "10:30"}'))
SETTINGS: dict[str, ParameterValue] = {
    "temperature": Decimal("0.7"),
    "max_tokens": Decimal(2048),
    "reasoning_effort": "alto",
}
ANSWER = '{"decisioni": []}'
FORMAT = AnswerFormat("decisioni", {"type": "object", "properties": {}, "required": [], "additionalProperties": False})
TIMED_OUT, REFUSED = "timed out", "connection refused"
USAGE: dict[str, object] = {"prompt_tokens": 2000, "completion_tokens": 500, "cost": 0.0031}
REPLY: dict[str, object] = {"choices": [{"message": {"role": "assistant", "content": ANSWER}}], "usage": USAGE}


class OpenRouter:
    """The API of OpenRouter in memory, recording the requests it receives."""

    def __init__(self, status: int = 200, body: object = REPLY, text: str | None = None) -> None:
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


def adapter_on(openrouter: OpenRouter) -> OpenRouterModelCallAdapter:
    return OpenRouterModelCallAdapter(httpx.Client(transport=httpx.MockTransport(openrouter.answer)))


def call(openrouter: OpenRouter, settings: dict[str, ParameterValue] | None = None) -> ModelReply:
    return adapter_on(openrouter).call(MODEL, KEY, SETTINGS if settings is None else settings, MESSAGES, FORMAT)


def test_the_call_reaches_openrouter_with_the_key_of_the_user_and_its_own_reasoning_field() -> None:
    openrouter = OpenRouter()

    reply = call(openrouter)

    request = openrouter.requests[0]
    assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
    assert request.headers["Authorization"] == f"Bearer {KEY.value('api_key')}"
    assert openrouter.sent == {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "system", "content": "regole"}, {"role": "user", "content": '{"ora": "10:30"}'}],
        "max_tokens": 2048,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "decisioni", "strict": True, "schema": dict(FORMAT.schema)},
        },
        "provider": {"require_parameters": True},
        "temperature": 0.7,
        "reasoning": {"effort": "high"},
    }
    assert reply == ModelReply(ANSWER, ModelUsage(2000, 500, Decimal("0.0031")))


@pytest.mark.parametrize(("effort", "expected"), [("basso", "low"), ("medio", "medium"), ("alto", "high")])
def test_the_reasoning_levels_become_the_names_of_openrouter(effort: str, expected: str) -> None:
    openrouter = OpenRouter()

    call(openrouter, {"reasoning_effort": effort})

    assert openrouter.sent["reasoning"] == {"effort": expected}


def test_without_settings_the_defaults_apply() -> None:
    openrouter = OpenRouter()

    call(openrouter, {})

    assert openrouter.sent["max_tokens"] == 4096
    assert not {"temperature", "reasoning"} & set(openrouter.sent)


def test_without_a_reported_cost_the_prices_of_the_catalog_apply() -> None:
    reply = call(OpenRouter(body={**REPLY, "usage": {"prompt_tokens": 1, "completion_tokens": 2}}))

    assert reply.usage == ModelUsage(1, 2, None)


@pytest.mark.parametrize("status", [401, 403])
def test_a_key_rejected_by_openrouter_is_a_permanent_error(status: int) -> None:
    with pytest.raises(ModelKeyRejectedError) as raised:
        call(OpenRouter(status, {"error": {"code": status, "message": "No auth credentials found"}}))

    assert str(raised.value) == "chiave del fornitore non valida: openrouter"
    assert raised.value.permanent


def test_no_credit_left_at_openrouter_is_a_permanent_error() -> None:
    with pytest.raises(ModelCreditExhaustedError) as raised:
        call(OpenRouter(402, {"error": {"code": 402, "message": "Insufficient credits"}}))

    assert raised.value.permanent


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503])
def test_any_other_refusal_is_transient_with_the_message_of_openrouter(status: int) -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(OpenRouter(status, {"error": {"code": status, "message": "No   endpoints\nfound"}}))

    assert raised.value.original == f"{status} No endpoints found"
    assert not raised.value.permanent


def test_a_refusal_that_echoes_the_key_never_carries_it() -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(OpenRouter(500, text=f"upstream rejected header Bearer {KEY.value('api_key')}"))

    assert KEY.value("api_key") not in str(raised.value)
    assert raised.value.__cause__ is None


@pytest.mark.parametrize(
    ("body", "text"),
    [({"choices": []}, None), ({"choices": [{"message": {"content": None}}], "usage": USAGE}, None), (None, "<html>")],
)
def test_an_answer_in_another_shape_is_transient(body: object, text: str | None) -> None:
    with pytest.raises(ModelUnavailableError, match="risposta del fornitore inattesa"):
        call(OpenRouter(200, body, text))


def test_a_timeout_is_transient_and_never_carries_the_request() -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(TIMED_OUT, request=request)

    adapter = OpenRouterModelCallAdapter(httpx.Client(transport=httpx.MockTransport(slow)))
    with pytest.raises(ModelUnavailableError, match=r"tempo di risposta scaduto$") as raised:
        adapter.call(MODEL, KEY, {}, MESSAGES, FORMAT)

    assert raised.value.__cause__ is None


def test_a_refused_connection_is_transient_and_never_carries_the_request() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    adapter = OpenRouterModelCallAdapter(httpx.Client(transport=httpx.MockTransport(refuse)))
    with pytest.raises(ModelUnavailableError, match=r"ConnectError$") as raised:
        adapter.call(MODEL, KEY, {}, MESSAGES, FORMAT)

    assert raised.value.__cause__ is None


# ADR-uso-riportato-nell-errore-della-chiamata-al-modello: a call OpenRouter may have charged says so in its error.
def test_an_answer_without_text_keeps_the_usage_openrouter_reported() -> None:
    body = {"choices": [{"message": {"role": "assistant", "content": None}}], "usage": USAGE}

    with pytest.raises(ModelUnavailableError, match="risposta del fornitore inattesa") as raised:
        call(OpenRouter(200, body))

    assert raised.value.usage == ModelUsage(2000, 500, Decimal("0.0031"))
    assert raised.value.sent


@pytest.mark.parametrize(
    ("body", "text"),
    [
        ({"choices": []}, None),
        ({"choices": [{"message": {"content": ANSWER}}], "usage": {"prompt_tokens": -1, "completion_tokens": 2}}, None),
        (None, "<html>"),
    ],
    ids=["no-usage", "invalid-usage", "not-json"],
)
def test_an_answer_without_a_readable_usage_was_sent_without_usage(body: object, text: str | None) -> None:
    with pytest.raises(ModelUnavailableError, match="risposta del fornitore inattesa") as raised:
        call(OpenRouter(200, body, text))

    assert (raised.value.usage, raised.value.sent) == (None, True)


def test_a_refusal_after_the_request_went_out_was_sent_without_usage() -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(OpenRouter(503, {"error": {"code": 503, "message": "busy"}}))

    assert (raised.value.usage, raised.value.sent) == (None, True)


def test_a_timeout_after_the_request_went_out_was_sent_without_usage() -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(TIMED_OUT, request=request)

    adapter = OpenRouterModelCallAdapter(httpx.Client(transport=httpx.MockTransport(slow)))
    with pytest.raises(ModelUnavailableError) as raised:
        adapter.call(MODEL, KEY, {}, MESSAGES, FORMAT)

    assert (raised.value.usage, raised.value.sent) == (None, True)


@pytest.mark.parametrize(
    "failure",
    [httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout],
    ids=["refused", "connect-timeout", "pool-timeout"],
)
def test_a_request_that_never_went_out_was_not_sent(failure: type[httpx.TransportError]) -> None:
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise failure(REFUSED, request=request)

    adapter = OpenRouterModelCallAdapter(httpx.Client(transport=httpx.MockTransport(unreachable)))
    with pytest.raises(ModelUnavailableError) as raised:
        adapter.call(MODEL, KEY, {}, MESSAGES, FORMAT)

    assert not raised.value.sent
