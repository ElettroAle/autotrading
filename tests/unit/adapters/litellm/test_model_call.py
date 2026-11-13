"""The model call through the LiteLLM proxy, served in memory in the shapes the proxy answers with (ADR 0101)."""

import json
from collections.abc import Callable
from decimal import Decimal

import httpx2
import pytest
from openai import OpenAI

from autotrading.adapters.outbound.litellm.model_call import (
    LiteLlmModelCallAdapter,
    litellm_model_call,
)
from autotrading.application.agent.errors import (
    ModelCreditExhaustedError,
    ModelKeyRejectedError,
    ModelUnavailableError,
)
from autotrading.application.agent.ports import ModelReply
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.agent.model_parameter import ParameterValue
from autotrading.domain.agent.model_usage import ModelUsage
from autotrading.domain.agent.provider_key import ProviderKey

PROXY_URL = "http://litellm:4000"
MASTER_KEY = "sk-master-of-the-installation"
KEY = ProviderKey("K-FAKE-MODEL-KEY")
MESSAGES = (ModelMessage(MessageRole.SYSTEM, "regole"), ModelMessage(MessageRole.USER, '{"ora_corrente": "10:30"}'))
SENT_MESSAGES = [{"role": "system", "content": "regole"}, {"role": "user", "content": '{"ora_corrente": "10:30"}'}]
SETTINGS: dict[str, ParameterValue] = {
    "temperature": Decimal("0.7"),
    "max_tokens": Decimal(2048),
    "reasoning_effort": "alto",
}
ANSWER = '{"decisioni": []}'
TIMED_OUT, REFUSED = "timed out", "connection refused"
USAGE: dict[str, object] = {"prompt_tokens": 2000, "completion_tokens": 500, "total_tokens": 2500}
REPLY: dict[str, object] = {
    "id": "chatcmpl-1",
    "object": "chat.completion",
    "created": 1,
    "model": "openai/gpt-4.1-mini",
    "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": ANSWER}}],
    "usage": USAGE,
}
ROUTING_NOISE = ". Received Model Group=openai/gpt\nAvailable Model Group Fallbacks=None"

type Answer = Callable[[httpx2.Request], httpx2.Response]


class Proxy:
    """The LiteLLM proxy in memory, recording the requests it receives."""

    def __init__(self, status: int = 200, body: object = REPLY, text: str | None = None) -> None:
        self.requests: list[httpx2.Request] = []
        self._status, self._body, self._text = status, body, text

    def answer(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if self._text is not None:
            return httpx2.Response(self._status, text=self._text)
        return httpx2.Response(self._status, json=self._body)

    @property
    def sent(self) -> dict[str, object]:
        body: dict[str, object] = json.loads(self.requests[0].content)
        return body


def adapter_on(answer: Answer) -> LiteLlmModelCallAdapter:
    client = OpenAI(
        api_key=MASTER_KEY,
        base_url=PROXY_URL,
        max_retries=0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(answer)),
    )
    return LiteLlmModelCallAdapter(client)


def call(proxy: Proxy, model: str, settings: dict[str, ParameterValue] | None = None) -> ModelReply:
    return adapter_on(proxy.answer).call(model, KEY, SETTINGS if settings is None else settings, MESSAGES)


def refusal(status: int, message: str) -> Proxy:
    return Proxy(status, {"error": {"message": message, "type": None, "param": None, "code": str(status)}})


def test_the_request_reaches_the_proxy_with_the_master_key_and_the_key_of_the_user_in_the_body() -> None:
    proxy = Proxy()

    call(proxy, "openai/gpt-4.1-mini")

    request = proxy.requests[0]
    assert str(request.url) == f"{PROXY_URL}/chat/completions"
    assert request.headers["Authorization"] == f"Bearer {MASTER_KEY}"
    assert proxy.sent["api_key"] == KEY.secret


def test_openai_gets_a_json_answer_and_the_reasoning_effort() -> None:
    proxy = Proxy()

    reply = call(proxy, "openai/gpt-4.1-mini")

    assert reply == ModelReply(ANSWER, ModelUsage(2000, 500, None))
    assert proxy.sent == {
        "model": "openai/gpt-4.1-mini",
        "messages": SENT_MESSAGES,
        "max_tokens": 2048,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
        "reasoning_effort": "high",
        "api_key": KEY.secret,
    }


def test_deepseek_gets_a_json_answer_and_the_reasoning_effort() -> None:
    proxy = Proxy()

    call(proxy, "deepseek/deepseek-chat")

    assert proxy.sent == {
        "model": "deepseek/deepseek-chat",
        "messages": SENT_MESSAGES,
        "max_tokens": 2048,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
        "reasoning_effort": "high",
        "api_key": KEY.secret,
    }


def test_anthropic_gets_the_effort_of_its_output_and_no_thinking_budget() -> None:
    proxy = Proxy()

    call(proxy, "anthropic/claude-sonnet-5-5")

    assert proxy.sent == {
        "model": "anthropic/claude-sonnet-5-5",
        "messages": SENT_MESSAGES,
        "max_tokens": 2048,
        "temperature": 0.7,
        "output_config": {"effort": "high"},
        "api_key": KEY.secret,
    }


def test_openrouter_gets_its_reasoning_object_and_reports_the_cost() -> None:
    proxy = Proxy(body={**REPLY, "usage": {**USAGE, "cost": 0.0031}})

    reply = call(proxy, "openrouter/deepseek/deepseek-chat")

    assert reply == ModelReply(ANSWER, ModelUsage(2000, 500, Decimal("0.0031")))
    assert proxy.sent == {
        "model": "openrouter/deepseek/deepseek-chat",
        "messages": SENT_MESSAGES,
        "max_tokens": 2048,
        "temperature": 0.7,
        "reasoning": {"effort": "high"},
        "api_key": KEY.secret,
    }


@pytest.mark.parametrize(("effort", "expected"), [("basso", "low"), ("medio", "medium"), ("alto", "high")])
def test_the_reasoning_levels_become_the_names_of_the_provider(effort: str, expected: str) -> None:
    proxy = Proxy()

    call(proxy, "openai/o4-mini", {"reasoning_effort": effort})

    assert proxy.sent["reasoning_effort"] == expected


@pytest.mark.parametrize("model", ["openai/gpt", "deepseek/deepseek-chat", "openrouter/x/y", "anthropic/claude"])
def test_without_settings_the_defaults_apply(model: str) -> None:
    proxy = Proxy()

    call(proxy, model, {})

    sent = proxy.sent
    assert sent["max_tokens"] == 4096
    assert not {"temperature", "reasoning_effort", "reasoning", "output_config"} & set(sent)


def test_a_provider_without_a_field_of_its_own_takes_the_reasoning_effort_of_litellm() -> None:
    proxy = Proxy()

    call(proxy, "gemini/gemini-pro")

    assert proxy.sent["reasoning_effort"] == "high"
    assert "response_format" not in proxy.sent


@pytest.mark.parametrize("status", [401, 403])
@pytest.mark.parametrize("model", ["openrouter/x/y", "anthropic/claude", "openai/gpt", "deepseek/deepseek-chat"])
def test_a_key_rejected_by_the_provider_is_a_permanent_error(status: int, model: str) -> None:
    proxy = refusal(status, f"litellm.AuthenticationError: Incorrect API key provided: {KEY.secret}{ROUTING_NOISE}")

    with pytest.raises(ModelKeyRejectedError) as raised:
        call(proxy, model)

    assert str(raised.value) == f"chiave del fornitore non valida: {model.partition('/')[0]}"
    assert raised.value.permanent


def test_a_master_key_the_proxy_does_not_know_is_transient() -> None:
    proxy = Proxy(400, {"error": {"message": "No connected db.", "type": "no_db_connection", "code": "400"}})

    with pytest.raises(ModelUnavailableError) as raised:
        call(proxy, "openai/gpt")

    assert raised.value.original == "400 No connected db."
    assert not raised.value.permanent


@pytest.mark.parametrize("model", ["openrouter/x/y", "deepseek/deepseek-chat"])
def test_payment_required_is_an_exhausted_credit(model: str) -> None:
    proxy = refusal(
        402, f'litellm.APIError: {{"error": {{"code": 402, "message": "Insufficient credits"}}}}{ROUTING_NOISE}'
    )

    with pytest.raises(ModelCreditExhaustedError) as raised:
        call(proxy, model)

    assert str(raised.value) == f"credito esaurito presso {model.partition('/')[0]}"
    assert raised.value.permanent


@pytest.mark.parametrize(
    "message",
    [
        f"litellm.RateLimitError: OpenAIException - You exceeded your current quota{ROUTING_NOISE}",
        "litellm.RateLimitError: {'code': 'insufficient_quota'}",
    ],
)
def test_an_exhausted_openai_quota_is_an_exhausted_credit(message: str) -> None:
    with pytest.raises(ModelCreditExhaustedError, match=r"^credito esaurito presso openai$"):
        call(refusal(429, message), "openai/gpt")


def test_a_rate_limit_is_transient_with_the_original_message_without_the_routing_of_the_proxy() -> None:
    proxy = refusal(429, f"litellm.RateLimitError: RateLimitError: OpenAIException - Rate limit reached{ROUTING_NOISE}")

    with pytest.raises(ModelUnavailableError) as raised:
        call(proxy, "openai/gpt")

    assert raised.value.original == "429 litellm.RateLimitError: RateLimitError: OpenAIException - Rate limit reached"
    assert not raised.value.permanent


@pytest.mark.parametrize(
    ("status", "body", "text", "original"),
    [
        (
            500,
            {"error": {"message": "litellm.InternalServerError: Overloaded"}},
            None,
            "500 litellm.InternalServerError: Overloaded",
        ),
        (502, None, "<html>\n  Bad   gateway\n</html>", "502 <html> Bad gateway </html>"),
        (500, {"error": "boom"}, None, "500 boom"),
        (503, ["unavailable"], None, "503 ['unavailable']"),
        (504, None, "", "504 "),
        (400, {"error": {"message": 42}}, None, "400 {'message': 42}"),
    ],
)
def test_other_refusals_are_transient_with_the_original_message(
    status: int, body: object, text: str | None, original: str
) -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(Proxy(status, body, text), "anthropic/claude")

    assert raised.value.original == original


def test_a_long_original_message_is_cut() -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(refusal(500, "x" * 1000), "openai/gpt")

    assert raised.value.original == "500 " + "x" * 300


def test_the_key_never_travels_in_a_transient_error() -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(refusal(500, f"upstream rejected header Bearer {KEY.secret}"), "openrouter/x/y")

    assert KEY.secret not in str(raised.value)
    assert raised.value.__cause__ is None


def test_a_timeout_is_transient() -> None:
    def slow(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout(TIMED_OUT, request=request)

    with pytest.raises(
        ModelUnavailableError, match=r"^fornitore IA non raggiungibile: openrouter: tempo di risposta scaduto$"
    ):
        adapter_on(slow).call("openrouter/x/y", KEY, {}, MESSAGES)


def test_an_unreachable_proxy_is_transient_and_carries_no_request() -> None:
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError(REFUSED, request=request)

    with pytest.raises(
        ModelUnavailableError, match=r"^fornitore IA non raggiungibile: openrouter: APIConnectionError$"
    ) as raised:
        adapter_on(refuse).call("openrouter/x/y", KEY, {}, MESSAGES)

    assert raised.value.__cause__ is None


@pytest.mark.parametrize(
    "body",
    [
        {**REPLY, "choices": []},
        {key: value for key, value in REPLY.items() if key != "usage"},
        {**REPLY, "usage": {**USAGE, "prompt_tokens": -1}},
        {**REPLY, "usage": {**USAGE, "cost": "free"}},
        {
            **REPLY,
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": None}}],
        },
    ],
)
def test_an_answer_in_another_shape_is_transient(body: object) -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(Proxy(200, body), "openai/gpt")

    assert raised.value.original == "risposta del fornitore inattesa"


def test_an_answer_that_is_not_json_is_transient() -> None:
    with pytest.raises(ModelUnavailableError, match=r"risposta del fornitore inattesa$"):
        call(Proxy(200, text="<html>ok</html>"), "openai/gpt")


def test_the_adapter_of_the_installation_talks_to_the_proxy_at_its_address() -> None:
    adapter = litellm_model_call("http://127.0.0.1:9", MASTER_KEY)

    with pytest.raises(ModelUnavailableError, match=r"APIConnectionError$"):
        adapter.call("openai/gpt", KEY, {}, MESSAGES)
