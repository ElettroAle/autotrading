from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Literal

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, omit
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params import ResponseFormatJSONObject

from autotrading.application.agent.errors import (
    ModelCreditExhaustedError,
    ModelKeyRejectedError,
    ModelUnavailableError,
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
DEFAULT_MAX_TOKENS = 4096
ORIGINAL_LIMIT = 300
KEY_REJECTED = frozenset({401, 403})
CREDIT_EXHAUSTED = 402
TOO_MANY_REQUESTS = 429
# The proxy keeps the message of OpenAI but not its code: either tells an exhausted quota from a rate limit.
QUOTA_EXHAUSTED = ("insufficient_quota", "exceeded your current quota")
# The proxy appends its routing to every message: it says nothing about the provider and is left out.
ROUTING_OF_THE_PROXY = ". Received Model Group="
UNEXPECTED_ANSWER = "risposta del fornitore inattesa"

type Settings = Mapping[str, ParameterValue]
type Effort = Literal["low", "medium", "high"]

EFFORTS: Mapping[str, Effort] = {"basso": "low", "medio": "medium", "alto": "high"}
JSON_ANSWER: ResponseFormatJSONObject = {"type": "json_object"}


class LiteLlmModelCallAdapter:
    """Calls the model of a flow through the LiteLLM proxy with the key of the user; used by the worker only.

    The key of the user travels only in the body of the request, for that request (RF-01.05, ADR 0101): it never
    reaches an error, a log or the context. The proxy itself is reached with the master key of the installation.
    """

    def __init__(self, client: OpenAI) -> None:
        self._client = client

    def call(self, model: str, key: ProviderKey, settings: Settings, messages: tuple[ModelMessage, ...]) -> ModelReply:
        provider = ProviderName(model.partition(PROVIDER_SEPARATOR)[0])
        completion = self._complete(provider, model, key, settings, messages)
        try:
            return _reply_of(completion)
        # The SDK hands back the raw text when the proxy answers 200 without JSON.
        except (AttributeError, IndexError, TypeError, InvalidOperation, InvalidModelUsageError) as error:
            raise ModelUnavailableError(provider, UNEXPECTED_ANSWER) from error

    def _complete(
        self,
        provider: ProviderName,
        model: str,
        key: ProviderKey,
        settings: Settings,
        messages: tuple[ModelMessage, ...],
    ) -> ChatCompletion:
        temperature, effort = settings.get("temperature"), settings.get("reasoning_effort")
        try:
            return self._client.chat.completions.create(
                model=model,
                messages=[_message(message) for message in messages],
                max_tokens=int(Decimal(settings.get("max_tokens", DEFAULT_MAX_TOKENS))),
                temperature=omit if temperature is None else float(Decimal(temperature)),
                # LiteLLM translates both for every provider and drops them where the model does not take them.
                response_format=JSON_ANSWER,
                reasoning_effort=omit if effort is None else EFFORTS[str(effort)],
                extra_body={"api_key": key.secret},
                timeout=TIMEOUT_SECONDS,
            )
        # The errors of the SDK carry the request, and with it the key in its body: they never travel as a cause.
        except APITimeoutError:
            raise ModelUnavailableError(provider, "tempo di risposta scaduto") from None
        except APIConnectionError as error:
            raise ModelUnavailableError(provider, type(error).__name__) from None
        except APIStatusError as error:
            raise _refusal(provider, key, error) from None


def litellm_model_call(url: str, master_key: str) -> LiteLlmModelCallAdapter:
    """The adapter of the installation: the proxy at its internal address, no retries (the next cycle retries)."""
    return LiteLlmModelCallAdapter(OpenAI(api_key=master_key, base_url=url, timeout=TIMEOUT_SECONDS, max_retries=0))


def _message(message: ModelMessage) -> ChatCompletionMessageParam:
    if message.role is MessageRole.SYSTEM:
        return ChatCompletionSystemMessageParam(role="system", content=message.content)
    return ChatCompletionUserMessageParam(role="user", content=message.content)


def _refusal(provider: ProviderName, key: ProviderKey, error: APIStatusError) -> Exception:
    status = error.status_code
    message = _original_message(error)
    if status in KEY_REJECTED:
        return ModelKeyRejectedError(provider)
    if status == CREDIT_EXHAUSTED or (status == TOO_MANY_REQUESTS and _quota_exhausted(message)):
        return ModelCreditExhaustedError(provider)
    # A provider may echo part of the request in its message: the key is masked before it can travel further.
    return ModelUnavailableError(provider, key.redact(f"{status} {message}"))


def _quota_exhausted(message: str) -> bool:
    return any(sign in message for sign in QUOTA_EXHAUSTED)


def _original_message(error: APIStatusError) -> str:
    body = error.body
    message = body.get("message") if isinstance(body, Mapping) else None
    # The SDK hands back the raw text as the body of an answer that is not JSON.
    text = message.partition(ROUTING_OF_THE_PROXY)[0] if isinstance(message, str) else str(body)
    return " ".join(text.split())[:ORIGINAL_LIMIT]


def _reply_of(completion: ChatCompletion) -> ModelReply:
    text = completion.choices[0].message.content
    usage = completion.usage
    if text is None or usage is None:
        raise InvalidModelUsageError
    return ModelReply(text, ModelUsage(usage.prompt_tokens, usage.completion_tokens, _reported_cost(usage.model_extra)))


def _reported_cost(extra: Mapping[str, object] | None) -> Decimal | None:
    """Only a cost the provider reports itself: otherwise the prices of the catalog apply (R1.4.6)."""
    reported = None if extra is None else extra.get("cost")
    if reported is None:
        return None
    return Decimal(str(reported))
