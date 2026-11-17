from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from autotrading.application.agent.errors import (
    ModelAnswerUnreadableError,
    ModelKeyMissingError,
    ModelUnavailableError,
)
from autotrading.application.agent.model_gateways import ModelGateways, gateway_of
from autotrading.application.agent.ports import (
    ModelReply,
    PausePort,
    ProviderKeyOpenerPort,
    ProviderKeyRepositoryPort,
)
from autotrading.domain.agent.agent_context import AgentContext
from autotrading.domain.agent.agent_response import AgentResponse
from autotrading.domain.agent.answer_format import DECISIONS_FORMAT
from autotrading.domain.agent.model_parameter import ParameterValue
from autotrading.domain.agent.model_usage import ModelPrices, ModelSpend, ModelUsage
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName

# Two more calls after the first, each after a longer pause: a provider that is down a moment is up again within the
# cycle, one that stays down fails the cycle (ADR ritentativo-del-modello-nel-ciclo).
RETRY_PAUSES_SECONDS = (5.0, 15.0)


@dataclass(frozen=True, slots=True)
class AskAgentCommand:
    model: str
    settings: Mapping[str, ParameterValue]
    context: AgentContext


@dataclass(frozen=True, slots=True)
class AgentAnswer:
    """The answer of the agent as the cycle keeps it, with what the call consumed and cost (R1.4.4-R1.4.6)."""

    response: AgentResponse
    usage: ModelUsage
    cost_usd: Decimal | None


class AskAgentUseCase:
    """Asks the model of the flow with the key of the tenant, in the worker, and reads its answer (R1.4.3-R1.4.6).

    A temporary failure of the provider is asked again in the same cycle, up to twice and after a longer pause each
    time, even if the provider may have charged it; a permanent failure or an answer that arrived unreadable is not (ADR
    ritentativo-del-modello-nel-ciclo, R1.4.5). The gateway that calls is the one whose catalog holds the model of the
    flow (ADR 0109).
    """

    def __init__(
        self,
        gateways: ModelGateways,
        keys: ProviderKeyRepositoryPort,
        opener: ProviderKeyOpenerPort,
        pause: PausePort,
    ) -> None:
        self._gateways = gateways
        self._keys = keys
        self._opener = opener
        self._pause = pause

    def execute(self, command: AskAgentCommand) -> AgentAnswer:
        definition, gateway = gateway_of(self._gateways, command.model)
        key = self._key_of(definition.provider)
        call = gateway.model_call()
        reply, spend = self._reply_of(
            lambda: call.call(definition.name, key, command.settings, command.context.messages(), DECISIONS_FORMAT),
            definition.prices,
        )
        return AgentAnswer(
            AgentResponse.read(reply.text, command.context.assets),
            reply.usage.plus(spend.usage),
            spend.with_call(reply.usage, reply.usage.cost_usd(definition.prices)).cost_usd,
        )

    def _reply_of(self, ask: Callable[[], ModelReply], prices: ModelPrices | None) -> tuple[ModelReply, ModelSpend]:
        """The reply, with what the failed calls before it spent; every failed call the provider may have charged
        carries its cost, priced as an answered one (R1.4.6).
        """
        spend = ModelSpend()
        for pause in RETRY_PAUSES_SECONDS:
            try:
                return ask(), spend
            except ModelUnavailableError as error:
                failed = error.priced(prices)
                spend = failed.spent_after(spend)
                if not _temporary(error):
                    raise failed.with_spend(spend) from error
            self._pause.pause(pause)
        try:
            return ask(), spend
        except ModelUnavailableError as error:
            failed = error.priced(prices)
            raise failed.with_spend(failed.spent_after(spend)) from error

    def _key_of(self, provider: ProviderName) -> ProviderKey:
        registered = self._keys.get(provider)
        if registered is None:
            raise ModelKeyMissingError(provider)
        return self._opener.open(registered)


def _temporary(error: ModelUnavailableError) -> bool:
    """An answer that arrived unreadable is not a failure of availability: asking again would not change it (R1.4.5)."""
    return not error.permanent and not isinstance(error, ModelAnswerUnreadableError)
