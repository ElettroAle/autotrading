from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

import httpx

from autotrading.application.agent.errors import (
    ModelAnswerTruncatedError,
    ModelCreditExhaustedError,
    ModelKeyRejectedError,
    ModelUnavailableError,
)
from autotrading.application.agent.ports import ModelReply
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.agent.answer_format import AnswerFormat
from autotrading.domain.agent.errors import InvalidModelUsageError
from autotrading.domain.agent.model_definition import PROVIDER_SEPARATOR
from autotrading.domain.agent.model_parameter import ParameterValue
from autotrading.domain.agent.model_usage import ModelUsage
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_key_field import API_KEY_FIELD
from autotrading.domain.agent.provider_name import ProviderName

API_URL = "https://openrouter.ai/api/v1"
# A model may think for a while before it answers; the cycle waits for it, not longer.
TIMEOUT_SECONDS = 120.0
OPENROUTER = ProviderName("openrouter")
PREFIX = OPENROUTER.value + PROVIDER_SEPARATOR
KEY_REJECTED = frozenset({401, 403})
CREDIT_EXHAUSTED = 402
ORIGINAL_LIMIT = 300
UNEXPECTED_ANSWER = "risposta del fornitore inattesa"
UNREADABLE = (KeyError, IndexError, TypeError, ValueError, InvalidOperation, InvalidModelUsageError)
# Failures before the request leaves: OpenRouter never received it, so it cannot have charged it.
NOT_SENT = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)
DEFAULT_MAX_TOKENS = 4096
# The model stopped at the token limit of the call, not at the end of its answer: what it wrote is not a decision.
CUT_AT_LIMIT = "length"
EFFORTS: Mapping[str, str] = {"basso": "low", "medio": "medium", "alto": "high"}
# Routed only to the providers that take every parameter: the format of the answer is enforced, never dropped.
REQUIRE_EVERY_PARAMETER: Mapping[str, bool] = {"require_parameters": True}

type Settings = Mapping[str, ParameterValue]


class OpenRouterModelCallAdapter:
    """Calls a model of OpenRouter on its API with the key of the user; used by the worker only (ADR 0109).

    The key of the user travels only in the header of the call of its flow (RF-01.05): it never reaches an error, a
    log or the context. OpenRouter reports the cost of every call, which the cycle records (R1.4.6).
    """

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def call(
        self,
        model: str,
        key: ProviderKey,
        settings: Settings,
        messages: tuple[ModelMessage, ...],
        answer: AnswerFormat,
    ) -> ModelReply:
        max_tokens = _max_tokens_of(settings)
        document = self._complete(key, _request(model, settings, max_tokens, messages, answer))
        # Whatever the answer looks like, the request went out and OpenRouter may have charged it (R1.4.6).
        try:
            usage = _usage_of(document)
        except UNREADABLE as error:
            raise _unusable(key, document, None) from error
        if _cut_at_limit(document):
            raise ModelAnswerTruncatedError(OPENROUTER, max_tokens, usage=usage, sent=True)
        try:
            return ModelReply(_text_of(document), usage)
        except UNREADABLE as error:
            raise _unusable(key, document, usage) from error

    def _complete(self, key: ProviderKey, request: Mapping[str, object]) -> object:
        try:
            response = self._client.post(
                f"{API_URL}/chat/completions",
                headers={"Authorization": f"Bearer {key.value(API_KEY_FIELD.name)}"},
                json=request,
                timeout=TIMEOUT_SECONDS,
            )
        # The errors of httpx carry the request, and with it the key in its header: they never travel as a cause.
        except NOT_SENT as error:
            raise ModelUnavailableError(OPENROUTER, _reason_of(error)) from None
        except httpx.HTTPError as error:
            raise ModelUnavailableError(OPENROUTER, _reason_of(error), sent=True) from None
        if response.status_code != httpx.codes.OK:
            raise _refusal(key, response.status_code, _original_message(response))
        try:
            document: object = response.json()
        except ValueError:
            raise ModelUnavailableError(OPENROUTER, UNEXPECTED_ANSWER, sent=True) from None
        return document


def _request(
    model: str, settings: Settings, max_tokens: int, messages: tuple[ModelMessage, ...], answer: AnswerFormat
) -> dict[str, object]:
    request: dict[str, object] = {
        "model": model.removeprefix(PREFIX),
        "messages": [{"role": _role(message), "content": message.content} for message in messages],
        "max_tokens": max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": answer.name, "strict": True, "schema": answer.schema},
        },
        "provider": REQUIRE_EVERY_PARAMETER,
    }
    temperature = settings.get("temperature")
    if temperature is not None:
        request["temperature"] = float(Decimal(temperature))
    effort = settings.get("reasoning_effort")
    if effort is not None:
        request["reasoning"] = {"effort": EFFORTS[str(effort)]}
    return request


def _max_tokens_of(settings: Settings) -> int:
    return int(Decimal(settings.get("max_tokens", DEFAULT_MAX_TOKENS)))


def _role(message: ModelMessage) -> str:
    return "system" if message.role is MessageRole.SYSTEM else "user"


def _refusal(key: ProviderKey, status: int, message: str, usage: ModelUsage | None = None) -> Exception:
    if status in KEY_REJECTED:
        return ModelKeyRejectedError(OPENROUTER)
    if status == CREDIT_EXHAUSTED:
        return ModelCreditExhaustedError(OPENROUTER)
    # A provider may echo part of the request in its message: the key is masked before it can travel further.
    return ModelUnavailableError(OPENROUTER, key.redact(f"{status} {message}"), usage=usage, sent=True)


def _unusable(key: ProviderKey, document: object, usage: ModelUsage | None) -> Exception:
    """The error OpenRouter puts in an answer when the provider behind it fails, with the code of that failure when it
    gives one; else an answer that cannot be read (ADR errore-di-openrouter-nella-risposta).
    """
    error = _error_of(document)
    message = error.get("message")
    if not isinstance(message, str):
        return ModelUnavailableError(OPENROUTER, UNEXPECTED_ANSWER, usage=usage, sent=True)
    code = error.get("code")
    if isinstance(code, int) and not isinstance(code, bool):
        return _refusal(key, code, _compact(message), usage)
    return ModelUnavailableError(OPENROUTER, key.redact(_compact(message)), usage=usage, sent=True)


def _original_message(response: httpx.Response) -> str:
    try:
        document: object = response.json()
    except ValueError:
        document = None
    message = _error_of(document).get("message")
    return _compact(message if isinstance(message, str) else response.text)


def _error_of(document: object) -> Mapping[str, object]:
    error = document.get("error") if isinstance(document, Mapping) else None
    return error if isinstance(error, Mapping) else {}


def _compact(text: str) -> str:
    return " ".join(text.split())[:ORIGINAL_LIMIT]


def _reason_of(error: httpx.HTTPError) -> str:
    if isinstance(error, httpx.TimeoutException):
        return "tempo di risposta scaduto"
    return type(error).__name__


def _usage_of(document: object) -> ModelUsage:
    if not isinstance(document, Mapping):
        raise InvalidModelUsageError
    usage = document["usage"]
    if not isinstance(usage, Mapping):
        raise InvalidModelUsageError
    cost = usage.get("cost")
    reported = None if cost is None else Decimal(str(cost))
    return ModelUsage(int(usage["prompt_tokens"]), int(usage["completion_tokens"]), reported)


def _cut_at_limit(document: object) -> bool:
    """The first choice ended at the token limit, with no text or only part of it (Bug 733)."""
    choices = document.get("choices") if isinstance(document, Mapping) else None
    if not isinstance(choices, list) or not choices:
        return False
    first = choices[0]
    return isinstance(first, Mapping) and first.get("finish_reason") == CUT_AT_LIMIT


def _text_of(document: object) -> str:
    if not isinstance(document, Mapping):
        raise InvalidModelUsageError
    text = document["choices"][0]["message"]["content"]
    if not isinstance(text, str):
        raise InvalidModelUsageError
    return text
