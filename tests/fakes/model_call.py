from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.application.agent.ports import ModelReply
from autotrading.domain.agent.agent_context import ModelMessage
from autotrading.domain.agent.model_parameter import ParameterValue
from autotrading.domain.agent.model_usage import ModelUsage
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.errors import AutotradingError


@dataclass(frozen=True, slots=True)
class ModelCall:
    model: str
    key: ProviderKey
    settings: Mapping[str, ParameterValue]
    messages: tuple[ModelMessage, ...]


@dataclass
class FakeModelCallAdapter:
    """The provider of the model: it answers what the test says, with the usage it reports, or fails."""

    text: str = '{"decisioni": []}'
    usage: ModelUsage = field(default_factory=lambda: ModelUsage(1000, 200, Decimal("0.001")))
    failure: AutotradingError | None = None
    calls: list[ModelCall] = field(default_factory=list)

    def call(
        self, model: str, key: ProviderKey, settings: Mapping[str, ParameterValue], messages: tuple[ModelMessage, ...]
    ) -> ModelReply:
        self.calls.append(ModelCall(model, key, settings, messages))
        if self.failure is not None:
            raise self.failure
        return ModelReply(self.text, self.usage)
