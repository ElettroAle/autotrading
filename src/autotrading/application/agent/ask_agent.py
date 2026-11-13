from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from autotrading.application.agent.errors import ModelKeyMissingError
from autotrading.application.agent.model_gateways import ModelGateways, gateway_of
from autotrading.application.agent.ports import ProviderKeyOpenerPort, ProviderKeyRepositoryPort
from autotrading.domain.agent.agent_context import AgentContext
from autotrading.domain.agent.agent_response import AgentResponse
from autotrading.domain.agent.model_parameter import ParameterValue
from autotrading.domain.agent.model_usage import ModelUsage
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName


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

    One call per cycle: a failing call fails the cycle, never retried in the same cycle (R1.4.5). The gateway that
    calls is the one whose catalog holds the model of the flow (ADR 0109).
    """

    def __init__(self, gateways: ModelGateways, keys: ProviderKeyRepositoryPort, opener: ProviderKeyOpenerPort) -> None:
        self._gateways = gateways
        self._keys = keys
        self._opener = opener

    def execute(self, command: AskAgentCommand) -> AgentAnswer:
        definition, gateway = gateway_of(self._gateways, command.model)
        key = self._key_of(definition.provider)
        reply = gateway.model_call().call(definition.name, key, command.settings, command.context.messages())
        return AgentAnswer(
            AgentResponse.read(reply.text, command.context.assets),
            reply.usage,
            reply.usage.cost_usd(definition.prices),
        )

    def _key_of(self, provider: ProviderName) -> ProviderKey:
        registered = self._keys.get(provider)
        if registered is None:
            raise ModelKeyMissingError(provider)
        return self._opener.open(registered)
