"""The model call through the LiteLLM library, on a completion that answers and fails as the library does (ADR 0148)."""

from collections.abc import Callable
from decimal import Decimal

import httpx
import litellm
import pytest
from litellm import exceptions

from autotrading.adapters.outbound.litellm.model_call import LiteLlmModelCallAdapter
from autotrading.application.agent.errors import (
    ModelAnswerUnreadableError,
    ModelCreditExhaustedError,
    ModelKeyRejectedError,
    ModelUnavailableError,
)
from autotrading.application.agent.ports import ModelReply
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.agent.answer_format import AnswerFormat
from autotrading.domain.agent.model_parameter import ParameterValue
from autotrading.domain.agent.model_usage import ModelUsage
from autotrading.domain.agent.provider_key import ProviderKey
from tests.support.provider_key import api_key_of

TIMEOUT_SECONDS = 120.0
KEY = api_key_of("K-FAKE-MODEL-KEY")
MESSAGES = (ModelMessage(MessageRole.SYSTEM, "regole"), ModelMessage(MessageRole.USER, '{"ora_corrente": "10:30"}'))
SENT_MESSAGES = [{"role": "system", "content": "regole"}, {"role": "user", "content": '{"ora_corrente": "10:30"}'}]
SETTINGS: dict[str, ParameterValue] = {
    "temperature": Decimal("0.7"),
    "max_tokens": Decimal(2048),
    "reasoning_effort": "alto",
}
ANSWER = '{"decisioni": []}'
FORMAT = AnswerFormat("decisioni", {"type": "object", "properties": {}, "required": [], "additionalProperties": False})
STRICT_FORMAT = {"type": "json_schema", "json_schema": {"name": "decisioni", "strict": True, "schema": FORMAT.schema}}
USAGE: dict[str, object] = {"prompt_tokens": 2000, "completion_tokens": 500, "total_tokens": 2500}
CHOICES: list[dict[str, object]] = [
    {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": ANSWER}}
]

type Failure = Callable[[], Exception]


def response(**fields: object) -> litellm.ModelResponse:
    return litellm.ModelResponse(**({"model": "gpt-4.1-mini", "choices": CHOICES, "usage": USAGE} | fields))


class Library:
    """The completion of the library, recording what it is asked and answering or failing as told."""

    def __init__(self, answer: object = None, failure: Failure | None = None, strict: bool = True) -> None:
        self.requests: list[dict[str, object]] = []
        self.asked_formats: list[str] = []
        self._strict = strict
        self._answer = response() if answer is None else answer
        self._failure = failure

    def completion(self, **request: object) -> object:
        self.requests.append(request)
        if self._failure is not None:
            raise self._failure()
        return self._answer

    def supports_response_schema(self, model: str) -> bool:
        self.asked_formats.append(model)
        return self._strict

    @property
    def sent(self) -> dict[str, object]:
        return self.requests[0]


def adapter_on(library: Library) -> LiteLlmModelCallAdapter:
    return LiteLlmModelCallAdapter(library.completion, library.supports_response_schema, TIMEOUT_SECONDS)


def call(library: Library, model: str, settings: dict[str, ParameterValue] | None = None) -> ModelReply:
    return adapter_on(library).call(model, KEY, SETTINGS if settings is None else settings, MESSAGES, FORMAT)


def failing(failure: Failure) -> Library:
    return Library(failure=failure)


type Refused = Callable[..., Exception]


def refusal(kind: Refused, message: str) -> Failure:
    return lambda: kind(message=message, llm_provider="openai", model="gpt")


def refusal_with_response(kind: Refused, status: int, message: str) -> Failure:
    answer = httpx.Response(status, request=httpx.Request("POST", "https://provider.test"))
    return lambda: kind(message=message, llm_provider="openai", model="gpt", response=answer)


@pytest.mark.parametrize(
    "model", ["anthropic/claude-sonnet-5-5", "openai/gpt-4.1-mini", "deepseek/deepseek-chat", "gemini/gemini-pro"]
)
def test_every_provider_gets_the_same_request_of_the_openai_api_with_the_key_of_the_user(model: str) -> None:
    library = Library()

    call(library, model)

    assert library.sent == {
        "model": model,
        "messages": SENT_MESSAGES,
        "api_key": KEY.value("api_key"),
        "max_tokens": 2048,
        "temperature": 0.7,
        "response_format": STRICT_FORMAT,
        "reasoning_effort": "high",
        "drop_params": True,
        "num_retries": 0,
        "timeout": TIMEOUT_SECONDS,
    }


def test_a_model_the_library_declares_without_a_strict_format_is_asked_for_any_json() -> None:
    """ADR risposta-del-modello-con-schema-rigido: a capability the library declares, never a branch per provider."""
    library = Library(strict=False)

    call(library, "deepseek/deepseek-chat")

    assert library.asked_formats == ["deepseek/deepseek-chat"]
    assert library.sent["response_format"] == {"type": "json_object"}


def test_every_field_of_the_key_travels_as_the_parameter_of_the_call_it_names() -> None:
    """R2.3.9, ADR 0159: a provider that asks more than the key gets each field by its name, in this call only."""
    library = Library()
    key = ProviderKey({"api_key": "K-AZURE", "api_base": "https://models.example.test", "api_version": "2026-01"})

    adapter_on(library).call("azure/gpt-4o", key, SETTINGS, MESSAGES, FORMAT)

    assert {name: library.sent[name] for name in ("api_key", "api_base", "api_version")} == dict(key.values)


def test_the_answer_and_what_the_call_consumed_are_the_reply() -> None:
    assert call(Library(), "openai/gpt-4.1-mini") == ModelReply(ANSWER, ModelUsage(2000, 500, None))


@pytest.mark.parametrize(("effort", "expected"), [("basso", "low"), ("medio", "medium"), ("alto", "high")])
def test_the_reasoning_levels_become_the_names_of_the_provider(effort: str, expected: str) -> None:
    library = Library()

    call(library, "openai/o4-mini", {"reasoning_effort": effort})

    assert library.sent["reasoning_effort"] == expected


@pytest.mark.parametrize("model", ["openai/gpt", "deepseek/deepseek-chat", "anthropic/claude"])
def test_without_settings_the_defaults_apply(model: str) -> None:
    library = Library()

    call(library, model, {})

    assert library.sent["max_tokens"] == 4096
    assert not {"temperature", "reasoning_effort"} & set(library.sent)


@pytest.mark.parametrize("model", ["anthropic/claude", "openai/gpt", "deepseek/deepseek-chat"])
def test_a_key_rejected_by_the_provider_is_a_permanent_error(model: str) -> None:
    failure = refusal(exceptions.AuthenticationError, f"Incorrect API key provided: {KEY.value('api_key')}")

    with pytest.raises(ModelKeyRejectedError) as raised:
        call(failing(failure), model)

    assert str(raised.value) == f"chiave del fornitore non valida: {model.partition('/')[0]}"
    assert raised.value.permanent
    assert raised.value.__cause__ is None


def test_a_key_without_permission_is_a_permanent_error() -> None:
    failure = refusal_with_response(exceptions.PermissionDeniedError, 403, "not allowed")

    with pytest.raises(ModelKeyRejectedError, match=r"^chiave del fornitore non valida: anthropic$"):
        call(failing(failure), "anthropic/claude")


@pytest.mark.parametrize("model", ["openai/gpt", "deepseek/deepseek-chat"])
def test_payment_required_is_an_exhausted_credit(model: str) -> None:
    with pytest.raises(ModelCreditExhaustedError) as raised:
        call(failing(refusal(exceptions.PaymentRequiredError, "Insufficient credits")), model)

    assert str(raised.value) == f"credito esaurito presso {model.partition('/')[0]}"
    assert raised.value.permanent


@pytest.mark.parametrize(
    "message", ["OpenAIException - You exceeded your current quota", "{'code': 'insufficient_quota'}"]
)
def test_an_exhausted_openai_quota_under_a_rate_limit_is_transient(message: str) -> None:
    # ADR permanenza-decisa-dall-errore-base: a 429 is never permanent, whatever its message says.
    with pytest.raises(ModelUnavailableError) as raised:
        call(failing(refusal(exceptions.RateLimitError, message)), "openai/gpt")

    assert not raised.value.permanent


def test_a_rate_limit_is_transient_with_the_original_message() -> None:
    failure = refusal(exceptions.RateLimitError, "OpenAIException - Rate limit reached")

    with pytest.raises(ModelUnavailableError) as raised:
        call(failing(failure), "openai/gpt")

    assert raised.value.original == "429 litellm.RateLimitError: OpenAIException - Rate limit reached"
    assert not raised.value.permanent


@pytest.mark.parametrize(
    ("failure", "original"),
    [
        (refusal(exceptions.InternalServerError, "Overloaded"), "500 litellm.InternalServerError: Overloaded"),
        (
            refusal(exceptions.BadGatewayError, "<html>\n  Bad   gateway\n</html>"),
            "502 litellm.BadGatewayError: <html> Bad gateway </html>",
        ),
        (refusal(exceptions.ServiceUnavailableError, "busy"), "503 litellm.ServiceUnavailableError: busy"),
        (refusal(exceptions.BadRequestError, "too long"), "400 litellm.BadRequestError: too long"),
        (refusal(exceptions.NotFoundError, "no such model"), "404 litellm.NotFoundError: no such model"),
        (refusal(exceptions.APIResponseValidationError, "odd"), "500 odd"),
        (
            lambda: exceptions.APIError(status_code=418, message="tea", llm_provider="openai", model="gpt"),
            "418 litellm.APIError: tea",
        ),
        (
            refusal_with_response(exceptions.UnprocessableEntityError, 422, "bad"),
            "422 litellm.UnprocessableEntityError: bad",
        ),
    ],
    ids=["internal", "gateway", "unavailable", "bad-request", "not-found", "validation", "api", "unprocessable"],
)
def test_other_refusals_are_transient_with_the_original_message(failure: Failure, original: str) -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(failing(failure), "anthropic/claude")

    assert raised.value.original == original
    assert not raised.value.permanent


def test_a_long_original_message_is_cut() -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(failing(refusal(exceptions.InternalServerError, "x" * 1000)), "openai/gpt")

    assert raised.value.original == "500 " + ("litellm.InternalServerError: " + "x" * 1000)[:300]


def test_the_key_never_travels_in_a_transient_error() -> None:
    failure = refusal(exceptions.InternalServerError, f"upstream rejected header Bearer {KEY.value('api_key')}")

    with pytest.raises(ModelUnavailableError) as raised:
        call(failing(failure), "openai/gpt")

    assert KEY.value("api_key") not in str(raised.value)
    assert raised.value.__cause__ is None


def test_a_timeout_is_transient() -> None:
    def slow() -> Exception:
        return exceptions.Timeout(message="timed out", model="gpt", llm_provider="openai")

    with pytest.raises(
        ModelUnavailableError, match=r"^fornitore IA non raggiungibile: openai: tempo di risposta scaduto$"
    ) as raised:
        call(failing(slow), "openai/gpt")

    assert raised.value.__cause__ is None


def test_an_unreachable_provider_is_transient_and_carries_no_request() -> None:
    def refused() -> Exception:
        return exceptions.APIConnectionError(message="connection refused", model="gpt", llm_provider="openai")

    with pytest.raises(
        ModelUnavailableError, match=r"^fornitore IA non raggiungibile: openai: APIConnectionError$"
    ) as raised:
        call(failing(refused), "openai/gpt")

    assert raised.value.__cause__ is None


@pytest.mark.parametrize(
    "answer",
    [
        response(choices=[]),
        litellm.ModelResponse(model="gpt", choices=CHOICES),
        response(usage={**USAGE, "prompt_tokens": -1}),
        response(choices=[{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": None}}]),
        "not a response",
    ],
    ids=["no-choice", "no-usage", "negative-tokens", "no-text", "not-a-response"],
)
def test_an_answer_in_another_shape_is_an_unreadable_answer(answer: object) -> None:
    with pytest.raises(ModelAnswerUnreadableError) as raised:
        call(Library(answer), "openai/gpt")

    assert raised.value.original == "risposta del fornitore inattesa"
    assert not raised.value.permanent


# ADR-uso-riportato-nell-errore-della-chiamata-al-modello: a call the provider may have charged says so in its error.
def test_an_answer_without_text_keeps_the_usage_the_provider_reported() -> None:
    no_text = [{"index": 0, "finish_reason": "length", "message": {"role": "assistant", "content": None}}]

    with pytest.raises(ModelAnswerUnreadableError) as raised:
        call(Library(response(choices=no_text)), "openai/gpt")

    assert raised.value.usage == ModelUsage(2000, 500, None)
    assert raised.value.sent


@pytest.mark.parametrize(
    "answer",
    [
        litellm.ModelResponse(model="gpt", choices=CHOICES),
        response(usage={**USAGE, "prompt_tokens": -1}),
        "not a response",
    ],
    ids=["no-usage", "negative-tokens", "not-a-response"],
)
def test_an_answer_without_a_readable_usage_was_sent_without_usage(answer: object) -> None:
    with pytest.raises(ModelAnswerUnreadableError) as raised:
        call(Library(answer), "openai/gpt")

    assert (raised.value.usage, raised.value.sent) == (None, True)


def test_a_timeout_was_sent_without_usage() -> None:
    def slow() -> Exception:
        return exceptions.Timeout(message="timed out", model="gpt", llm_provider="openai")

    with pytest.raises(ModelUnavailableError) as raised:
        call(failing(slow), "openai/gpt")

    assert (raised.value.usage, raised.value.sent) == (None, True)


def test_a_refusal_after_the_request_went_out_was_sent_without_usage() -> None:
    with pytest.raises(ModelUnavailableError) as raised:
        call(failing(refusal(exceptions.InternalServerError, "Overloaded")), "openai/gpt")

    assert (raised.value.usage, raised.value.sent) == (None, True)


def test_an_unreachable_provider_was_not_sent() -> None:
    def refused() -> Exception:
        return exceptions.APIConnectionError(message="connection refused", model="gpt", llm_provider="openai")

    with pytest.raises(ModelUnavailableError) as raised:
        call(failing(refused), "openai/gpt")

    assert not raised.value.sent
