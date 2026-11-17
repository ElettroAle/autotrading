import threading
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.application.agent.ports import ModelReply
from autotrading.domain.agent.agent_context import ModelMessage
from autotrading.domain.agent.answer_format import AnswerFormat
from autotrading.domain.agent.model_parameter import ParameterValue
from autotrading.domain.agent.model_usage import ModelUsage
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.errors import AutotradingError

HELD_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class ModelCall:
    model: str
    key: ProviderKey
    settings: Mapping[str, ParameterValue]
    messages: tuple[ModelMessage, ...]
    answer: AnswerFormat


@dataclass
class FakeModelCallAdapter:
    """The provider of the model: it answers what the test says, with the usage it reports, or fails.

    The failures of the first calls, one per call, come before the answer or the failure of every other call.
    """

    text: str = '{"decisioni": []}'
    usage: ModelUsage = field(default_factory=lambda: ModelUsage(1000, 200, Decimal("0.001")))
    failure: AutotradingError | None = None
    first_failures: list[AutotradingError] = field(default_factory=list)
    calls: list[ModelCall] = field(default_factory=list)
    # A test that needs a cycle in progress holds the call open until it releases the gate.
    gate: threading.Event | None = None
    entered: threading.Event = field(default_factory=threading.Event)

    def call(
        self,
        model: str,
        key: ProviderKey,
        settings: Mapping[str, ParameterValue],
        messages: tuple[ModelMessage, ...],
        answer: AnswerFormat,
    ) -> ModelReply:
        self.calls.append(ModelCall(model, key, settings, messages, answer))
        self.entered.set()
        if self.gate is not None:
            self.gate.wait(HELD_SECONDS)
        if self.first_failures:
            raise self.first_failures.pop(0)
        if self.failure is not None:
            raise self.failure
        return ModelReply(self.text, self.usage)
