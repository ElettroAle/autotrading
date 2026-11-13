from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TypedDict, cast

import httpx

from autotrading.application.agent.errors import (
    ModelCreditExhaustedError,
    ModelKeyRejectedError,
    ModelUnavailableError,
    UnsupportedProviderError,
)
from autotrading.application.agent.ports import ModelReply
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.agent.errors import InvalidModelUsageError
from autotrading.domain.agent.model_definition import PROVIDER_SEPARATOR
from autotrading.domain.agent.model_parameter import ParameterValue
from autotrading.domain.agent.model_usage import ModelUsage
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName

# A model may think for a while before it answers; the cycle waits for it, not longer.
TIMEOUT_SECONDS = 120.0
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 4096
ORIGINAL_LIMIT = 300
EFFORTS = {"basso": "low", "medio": "medium", "alto": "high"}
KEY_REJECTED = frozenset({401, 403})
CREDIT_EXHAUSTED = 402
TOO_MANY_REQUESTS = 429
INSUFFICIENT_QUOTA = "insufficient_quota"

type Settings = Mapping[str, ParameterValue]
type Document = Mapping[str, object]


class _ChatMessage(TypedDict):
    content: str


class _ChatChoice(TypedDict):
    message: _ChatMessage


class _ChatUsage(TypedDict, total=False):
    prompt_tokens: int
    completion_tokens: int
    cost: float | str | None


class _ChatDocument(TypedDict):
    """A chat completion as OpenAI, DeepSeek and OpenRouter answer it; a wrong shape fails while it is read."""

    choices: list[_ChatChoice]
    usage: _ChatUsage


class _AnthropicBlock(TypedDict, total=False):
    type: str
    text: str


class _AnthropicUsage(TypedDict):
    input_tokens: int
    output_tokens: int


class _AnthropicDocument(TypedDict):
    """A message as Anthropic answers it; a wrong shape fails while it is read."""

    content: list[_AnthropicBlock]
    usage: _AnthropicUsage


@dataclass(frozen=True, slots=True)
class _ProviderApi:
    """How one provider takes a request and gives back the answer and its usage (ADR 0039)."""

    url: str
    headers: Callable[[ProviderKey], dict[str, str]]
    body: Callable[[str, Settings, tuple[ModelMessage, ...]], dict[str, object]]
    reply: Callable[[object], ModelReply]


class HttpxModelCallAdapter:
    """Calls the model of a flow at its provider with the key of the user; used by the worker only (ADR 0007).

    The key travels only in the headers of the request: it never reaches an error, a log or the context.
    """

    def __init__(self, client: httpx.Client, apis: Mapping[str, _ProviderApi] | None = None) -> None:
        self._client = client
        self._apis = PROVIDER_APIS if apis is None else apis

    def call(self, model: str, key: ProviderKey, settings: Settings, messages: tuple[ModelMessage, ...]) -> ModelReply:
        provider_name, _, model_id = model.partition(PROVIDER_SEPARATOR)
        provider = ProviderName(provider_name)
        api = self._apis.get(provider.value)
        if api is None:
            raise UnsupportedProviderError(provider, (ProviderName(name) for name in self._apis))
        response = self._post(provider, api, key, api.body(model_id, settings, messages))
        _raise_for_refusal(provider, key, response)
        try:
            return api.reply(response.json())
        except (ValueError, KeyError, IndexError, TypeError, InvalidOperation, InvalidModelUsageError) as error:
            raise ModelUnavailableError(provider, "risposta del fornitore inattesa") from error

    def _post(
        self, provider: ProviderName, api: _ProviderApi, key: ProviderKey, body: dict[str, object]
    ) -> httpx.Response:
        try:
            return self._client.post(api.url, headers=api.headers(key), json=body, timeout=TIMEOUT_SECONDS)
        except httpx.TimeoutException:
            raise ModelUnavailableError(provider, "tempo di risposta scaduto") from None
        except httpx.HTTPError as error:
            raise ModelUnavailableError(provider, type(error).__name__) from None


def _raise_for_refusal(provider: ProviderName, key: ProviderKey, response: httpx.Response) -> None:
    if response.is_success:
        return
    status = response.status_code
    if status in KEY_REJECTED:
        raise ModelKeyRejectedError(provider)
    if status == CREDIT_EXHAUSTED or _quota_exhausted(response):
        raise ModelCreditExhaustedError(provider)
    # A provider may echo part of the request in its message: the key is masked before it can travel further.
    raise ModelUnavailableError(provider, key.redact(f"{status} {_original_message(response)}"))


def _quota_exhausted(response: httpx.Response) -> bool:
    """OpenAI answers 429 both for a rate limit and for an exhausted quota: only the code tells them apart."""
    return response.status_code == TOO_MANY_REQUESTS and _error_of(response).get("code") == INSUFFICIENT_QUOTA


def _original_message(response: httpx.Response) -> str:
    message = _error_of(response).get("message")
    text = message if isinstance(message, str) else response.text
    return " ".join(text.split())[:ORIGINAL_LIMIT]


def _error_of(response: httpx.Response) -> Document:
    try:
        document = response.json()
    except ValueError:
        return {}
    error = document.get("error") if isinstance(document, Mapping) else None
    return error if isinstance(error, Mapping) else {}


def _bearer(key: ProviderKey) -> dict[str, str]:
    return {"Authorization": f"Bearer {key.secret}"}


def _anthropic_headers(key: ProviderKey) -> dict[str, str]:
    return {"x-api-key": key.secret, "anthropic-version": ANTHROPIC_VERSION}


def _chat_messages(messages: tuple[ModelMessage, ...]) -> list[dict[str, str]]:
    return [{"role": message.role.value, "content": message.content} for message in messages]


def _temperature(settings: Settings) -> dict[str, object]:
    value = settings.get("temperature")
    return {} if value is None else {"temperature": float(Decimal(value))}


def _max_tokens(settings: Settings) -> int:
    return int(Decimal(settings.get("max_tokens", DEFAULT_MAX_TOKENS)))


def _effort(settings: Settings) -> str | None:
    value = settings.get("reasoning_effort")
    return None if value is None else EFFORTS[str(value)]


def _openai_body(model_id: str, settings: Settings, messages: tuple[ModelMessage, ...]) -> dict[str, object]:
    effort = _effort(settings)
    return {
        "model": model_id,
        "messages": _chat_messages(messages),
        "max_completion_tokens": _max_tokens(settings),
        "response_format": {"type": "json_object"},
        **_temperature(settings),
        **({} if effort is None else {"reasoning_effort": effort}),
    }


def _deepseek_body(model_id: str, settings: Settings, messages: tuple[ModelMessage, ...]) -> dict[str, object]:
    return {
        "model": model_id,
        "messages": _chat_messages(messages),
        "max_tokens": _max_tokens(settings),
        "response_format": {"type": "json_object"},
        **_temperature(settings),
    }


def _openrouter_body(model_id: str, settings: Settings, messages: tuple[ModelMessage, ...]) -> dict[str, object]:
    # Not every routed model supports a JSON response format: the format is asked in the system message only.
    effort = _effort(settings)
    return {
        "model": model_id,
        "messages": _chat_messages(messages),
        "max_tokens": _max_tokens(settings),
        **_temperature(settings),
        **({} if effort is None else {"reasoning": {"effort": effort}}),
    }


def _anthropic_body(model_id: str, settings: Settings, messages: tuple[ModelMessage, ...]) -> dict[str, object]:
    effort = _effort(settings)
    return {
        "model": model_id,
        "max_tokens": _max_tokens(settings),
        "system": "\n\n".join(message.content for message in messages if message.role is MessageRole.SYSTEM),
        "messages": [
            {"role": message.role.value, "content": message.content}
            for message in messages
            if message.role is not MessageRole.SYSTEM
        ],
        **_temperature(settings),
        **({} if effort is None else {"output_config": {"effort": effort}}),
    }


def _chat_reply(answer: object) -> ModelReply:
    document = cast("_ChatDocument", answer)
    usage = document["usage"]
    cost = usage.get("cost")
    return ModelReply(
        str(document["choices"][0]["message"]["content"]),
        ModelUsage(int(usage["prompt_tokens"]), int(usage["completion_tokens"]), _cost_of(cost)),
    )


def _anthropic_reply(answer: object) -> ModelReply:
    document = cast("_AnthropicDocument", answer)
    usage = document["usage"]
    text = "".join(block["text"] for block in document["content"] if block["type"] == "text")
    return ModelReply(text, ModelUsage(int(usage["input_tokens"]), int(usage["output_tokens"]), None))


def _cost_of(reported: object) -> Decimal | None:
    if reported is None:
        return None
    return Decimal(str(reported))


PROVIDER_APIS: Mapping[str, _ProviderApi] = {
    "anthropic": _ProviderApi(
        "https://api.anthropic.com/v1/messages", _anthropic_headers, _anthropic_body, _anthropic_reply
    ),
    "openai": _ProviderApi("https://api.openai.com/v1/chat/completions", _bearer, _openai_body, _chat_reply),
    "deepseek": _ProviderApi("https://api.deepseek.com/chat/completions", _bearer, _deepseek_body, _chat_reply),
    # OpenRouter reports the cost of every call in its usage (R1.4.6).
    "openrouter": _ProviderApi("https://openrouter.ai/api/v1/chat/completions", _bearer, _openrouter_body, _chat_reply),
}
