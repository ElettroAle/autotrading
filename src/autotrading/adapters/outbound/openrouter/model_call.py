from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

import httpx

from autotrading.application.agent.errors import (
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
        document = self._complete(key, _request(model, settings, messages, answer))
        # Whatever the answer looks like, the request went out and OpenRouter may have charged it (R1.4.6).
        try:
            usage = _usage_of(document)
        except UNREADABLE as error:
            raise ModelUnavailableError(OPENROUTER, UNEXPECTED_ANSWER, sent=True) from error
        try:
            return ModelReply(_text_of(document), usage)
        except UNREADABLE as error:
            raise ModelUnavailableError(OPENROUTER, UNEXPECTED_ANSWER, usage=usage, sent=True) from error

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
            raise _refusal(key, response)
        try:
            document: object = response.json()
        except ValueError:
            raise ModelUnavailableError(OPENROUTER, UNEXPECTED_ANSWER, sent=True) from None
        return document


def _request(
    model: str, settings: Settings, messages: tuple[ModelMessage, ...], answer: AnswerFormat
) -> dict[str, object]:
    request: dict[str, object] = {
        "model": model.removeprefix(PREFIX),
        "messages": [{"role": _role(message), "content": message.content} for message in messages],
        "max_tokens": int(Decimal(settings.get("max_tokens", DEFAULT_MAX_TOKENS))),
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


def _role(message: ModelMessage) -> str:
    return "system" if message.role is MessageRole.SYSTEM else "user"


def _refusal(key: ProviderKey, response: httpx.Response) -> Exception:
    status = response.status_code
    if status in KEY_REJECTED:
        return ModelKeyRejectedError(OPENROUTER)
    if status == CREDIT_EXHAUSTED:
        return ModelCreditExhaustedError(OPENROUTER)
    # A provider may echo part of the request in its message: the key is masked before it can travel further.
    return ModelUnavailableError(OPENROUTER, key.redact(f"{status} {_original_message(response)}"), sent=True)


def _original_message(response: httpx.Response) -> str:
    try:
        document: object = response.json()
    except ValueError:
        document = None
    error = document.get("error") if isinstance(document, Mapping) else None
    message = error.get("message") if isinstance(error, Mapping) else None
    text = message if isinstance(message, str) else response.text
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


def _text_of(document: object) -> str:
    if not isinstance(document, Mapping):
        raise InvalidModelUsageError
    text = document["choices"][0]["message"]["content"]
    if not isinstance(text, str):
        raise InvalidModelUsageError
    return text
