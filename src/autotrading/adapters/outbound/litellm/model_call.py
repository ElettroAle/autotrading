from collections.abc import Callable, Mapping
from decimal import Decimal

# The library weighs about 200 MiB once loaded: the API imports this module through the bootstrap and never loads it,
# only the worker does when it composes the gateway (ADR 0148).
lazy import litellm.exceptions

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
from autotrading.domain.agent.provider_name import ProviderName

# A model may think for a while before it answers; the cycle waits for it, not longer.
TIMEOUT_SECONDS = 120.0
DEFAULT_MAX_TOKENS = 4096
ORIGINAL_LIMIT = 300
KEY_REJECTED = frozenset({401, 403})
CREDIT_EXHAUSTED = 402
UNEXPECTED_ANSWER = "risposta del fornitore inattesa"
# The model stopped at the token limit of the call, not at the end of its answer: what it wrote is not a decision.
CUT_AT_LIMIT = "length"

type Settings = Mapping[str, ParameterValue]
type Completion = Callable[..., object]
type StrictFormatSupport = Callable[[str], bool]

EFFORTS: Mapping[str, str] = {"basso": "low", "medio": "medium", "alto": "high"}
ANY_JSON: Mapping[str, str] = {"type": "json_object"}


class LiteLlmModelCallAdapter:
    """Calls the model of a flow through the LiteLLM library with the key of the user; used by the worker only.

    The key of the user travels only in the call of its flow (RF-01.05, ADR 0148): it never reaches an error, a log or
    the context. No retry: the next cycle is the new attempt, a retry would spend the credit of the user again.
    """

    def __init__(
        self, completion: Completion, supports_strict_format: StrictFormatSupport, timeout_seconds: float
    ) -> None:
        self._completion = completion
        self._supports_strict_format = supports_strict_format
        self._timeout_seconds = timeout_seconds

    def call(
        self,
        model: str,
        key: ProviderKey,
        settings: Settings,
        messages: tuple[ModelMessage, ...],
        answer: AnswerFormat,
    ) -> ModelReply:
        provider = ProviderName(model.partition(PROVIDER_SEPARATOR)[0])
        max_tokens = _max_tokens_of(settings)
        request = _request(model, key, settings, max_tokens, messages)
        request["response_format"] = self._response_format(model, answer)
        reply = self._complete(provider, key, request)
        # Whatever the answer looks like, the request went out and the provider may have charged it (R1.4.6).
        try:
            usage = _usage_of(reply)
        except InvalidModelUsageError as error:
            raise ModelUnavailableError(provider, UNEXPECTED_ANSWER, sent=True) from error
        if _cut_at_limit(reply):
            raise ModelAnswerTruncatedError(provider, max_tokens, usage=usage, sent=True)
        try:
            return ModelReply(_text_of(reply), usage)
        except (IndexError, InvalidModelUsageError) as error:
            raise ModelUnavailableError(provider, UNEXPECTED_ANSWER, usage=usage, sent=True) from error

    def _response_format(self, model: str, answer: AnswerFormat) -> Mapping[str, object]:
        """Enforced where the library declares the model able to (ADR risposta-del-modello-con-schema-rigido).

        A capability the library declares for the model, never a branch per provider: any other model is asked for
        JSON and its answer is read like every other. The library never validates the answer itself: it would fail
        the call and lose the answer and its cost, which the cycle keeps (R1.4.5).
        """
        if not self._supports_strict_format(model):
            return ANY_JSON
        return {"type": "json_schema", "json_schema": {"name": answer.name, "strict": True, "schema": answer.schema}}

    def _complete(self, provider: ProviderName, key: ProviderKey, request: dict[str, object]) -> object:
        try:
            return self._completion(**request, drop_params=True, num_retries=0, timeout=self._timeout_seconds)
        # The errors of the library carry the request, and with it the key: they never travel as a cause.
        except litellm.exceptions.Timeout:
            raise ModelUnavailableError(provider, "tempo di risposta scaduto", sent=True) from None
        # The library raises it when the provider could not be reached: the request never got there.
        except litellm.exceptions.APIConnectionError as error:
            raise ModelUnavailableError(provider, type(error).__name__) from None
        except (
            litellm.exceptions.AuthenticationError,
            litellm.exceptions.PermissionDeniedError,
            litellm.exceptions.NotFoundError,
            litellm.exceptions.BadRequestError,
            litellm.exceptions.UnprocessableEntityError,
            litellm.exceptions.RateLimitError,
            litellm.exceptions.InternalServerError,
            litellm.exceptions.ServiceUnavailableError,
            litellm.exceptions.BadGatewayError,
            litellm.exceptions.APIError,
            litellm.exceptions.APIResponseValidationError,
        ) as error:
            raise _refusal(provider, key, error.status_code, error.message) from None


def _request(
    model: str, key: ProviderKey, settings: Settings, max_tokens: int, messages: tuple[ModelMessage, ...]
) -> dict[str, object]:
    """Only the parameters of the OpenAI API, for every provider: translating them is the work of LiteLLM (ADR 0109)."""
    request: dict[str, object] = {
        "model": model,
        "messages": [{"role": _role(message), "content": message.content} for message in messages],
        "max_tokens": max_tokens,
    }
    # The key travels as the parameters its provider declared, by name, in this call only (ADR 0159).
    request.update(key.values)
    temperature = settings.get("temperature")
    if temperature is not None:
        request["temperature"] = float(Decimal(temperature))
    effort = settings.get("reasoning_effort")
    if effort is not None:
        request["reasoning_effort"] = EFFORTS[str(effort)]
    return request


def _max_tokens_of(settings: Settings) -> int:
    return int(Decimal(settings.get("max_tokens", DEFAULT_MAX_TOKENS)))


def _role(message: ModelMessage) -> str:
    return "system" if message.role is MessageRole.SYSTEM else "user"


def _refusal(provider: ProviderName, key: ProviderKey, status: int, message: str) -> Exception:
    if status in KEY_REJECTED:
        return ModelKeyRejectedError(provider)
    if status == CREDIT_EXHAUSTED:
        return ModelCreditExhaustedError(provider)
    # A provider may echo part of the request in its message: the key is masked before it can travel further.
    return ModelUnavailableError(provider, key.redact(f"{status} {_compact(message)}"), sent=True)


def _compact(message: str) -> str:
    return " ".join(message.split())[:ORIGINAL_LIMIT]


def _usage_of(answer: object) -> ModelUsage:
    """No reported cost: the providers of the library do not report one, the prices of the catalog apply (R1.4.6)."""
    usage = getattr(answer, "usage", None) if isinstance(answer, litellm.ModelResponse) else None
    if not isinstance(usage, litellm.Usage):
        raise InvalidModelUsageError
    return ModelUsage(usage.prompt_tokens, usage.completion_tokens, None)


def _cut_at_limit(answer: object) -> bool:
    """The first choice ended at the token limit, with no text or only part of it, in the names of the OpenAI API that
    the library gives every provider (Bug 733).
    """
    if not isinstance(answer, litellm.ModelResponse) or not answer.choices:
        return False
    first = answer.choices[0]
    return isinstance(first, litellm.Choices) and first.finish_reason == CUT_AT_LIMIT


def _text_of(answer: object) -> str:
    if not isinstance(answer, litellm.ModelResponse):
        raise InvalidModelUsageError
    choice = answer.choices[0]
    text = choice.message.content if isinstance(choice, litellm.Choices) else None
    if not isinstance(text, str):
        raise InvalidModelUsageError
    return text
