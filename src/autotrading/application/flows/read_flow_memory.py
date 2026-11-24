from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.application.flows.ports import AccountActivityPort, FlowRepositoryPort, PastDecisionsPort
from autotrading.application.flows.remembered_decisions import remembered_decisions
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.memory_entry import AssetMemory


@dataclass(frozen=True, slots=True)
class ReadFlowMemoryCommand:
    flow_id: FlowId


class ReadFlowMemoryUseCase:
    """The memory the agent of the flow would receive if its cycle started now, for every asset; None when the memory
    of the flow is off, without reading anything (R5.3.4, ADR memoria-del-flusso-dalle-decisioni-operative-precedenti).

    The PnL of a position still open is the one its account shows now, as the cycle reads it from the exchange.
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        decisions: PastDecisionsPort,
        activity: AccountActivityPort,
        clock: Callable[[], datetime],
    ) -> None:
        self._flows = flows
        self._decisions = decisions
        self._activity = activity
        self._clock = clock

    def execute(self, command: ReadFlowMemoryCommand) -> tuple[AssetMemory, ...] | None:
        flow = self._flows.get(command.flow_id)
        if not flow.configuration.memory.active:
            return None
        return remembered_decisions(
            self._decisions, flow.id.value, flow.configuration, self._clock(), self._unrealized_pnl(flow)
        )

    def _unrealized_pnl(self, flow: Flow) -> dict[str, Decimal]:
        """A draft without an account holds no position."""
        if flow.account_id is None:
            return {}
        positions = self._activity.execute(flow.account_id).positions
        held = flow.configuration.held(positions, lambda position: position.asset)
        return {position.asset: position.unrealized_pnl for position in held}
