from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import AccountActivityPort, FlowRepositoryPort
from autotrading.application.flows.remembered_decisions import MemoryReadings, remembered_decisions
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.memory_entry import AssetMemory


@dataclass(frozen=True, slots=True)
class ReadFlowMemoryCommand:
    flow_id: FlowId


@dataclass(frozen=True, slots=True)
class FlowMemoryReading:
    """The memory of the flow as the user consults it: whether it is on and, only then, what every asset gives."""

    active: bool
    assets: tuple[AssetMemory, ...]

    @classmethod
    def of(cls, memory: tuple[AssetMemory, ...] | None) -> FlowMemoryReading:
        if memory is None:
            return cls(active=False, assets=())
        return cls(active=True, assets=memory)


class ReadFlowMemoryUseCase:
    """The memory the agent of the flow would receive if its cycle started now, for every asset; off and empty when
    the memory of the flow is off, without reading anything (R5.3.4, ADR
    memoria-del-flusso-dalle-decisioni-operative-precedenti).

    The PnL of a position still open is the one its account shows now, as the cycle reads it from the exchange; the
    summary of the closed positions is in the currency of that account (R5.3.7).
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        memory: MemoryReadings,
        activity: AccountActivityPort,
        clock: Callable[[], datetime],
    ) -> None:
        self._flows = flows
        self._memory = memory
        self._activity = activity
        self._clock = clock

    def execute(self, command: ReadFlowMemoryCommand) -> FlowMemoryReading:
        flow = self._flows.get(command.flow_id)
        memory = remembered_decisions(
            self._memory, flow.id.value, flow.configuration, self._clock(), lambda: self._account_of(flow)
        )
        return FlowMemoryReading.of(memory)

    def _account_of(self, flow: Flow) -> AccountActivity | None:
        """A draft has no account."""
        if flow.account_id is None:
            return None
        return self._activity.execute(flow.account_id)
