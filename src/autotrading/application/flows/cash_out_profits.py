import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.application.flows.close_flow_positions import CloseFlowPositionsCommand, CloseFlowPositionsUseCase
from autotrading.application.flows.ports import FlowRepositoryPort, LedgerRecordingPort
from autotrading.application.flows.read_flow_state import ReadFlowStateCommand, ReadFlowStateUseCase
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.cash_out import CashOutOutcome, cash_out_capital
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.tenancy.user_id import UserId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class CashOutProfitsCommand:
    flow_id: FlowId
    # Who closes the positions: each closing order is recorded as theirs (R0.3.2).
    user_id: UserId
    # None keeps the capital allocated now (R3.4.1).
    capital: Decimal | None = None


@dataclass(frozen=True, slots=True)
class CashOutPorts:
    flow_state: ReadFlowStateUseCase
    closings: CloseFlowPositionsUseCase
    ledger: LedgerRecordingPort
    clock: Callable[[], datetime]


class CashOutProfitsUseCase:
    """Closes every position of a flow and frees its value above the capital it keeps (R3.4.1, ADR
    incasso-dei-profitti).

    Nothing closes before the checks: a flow without profits, or a capital out of range, is refused as it is. A closing
    that fails frees nothing and comes back with its reason. Otherwise the executions of the closings enter the ledger,
    so the value freed is the real one, fees included; the checks hold on that value too, then the capital, when it
    changes, and the cash-out are recorded together. The flow keeps its status.
    """

    def __init__(self, flows: FlowRepositoryPort, ports: CashOutPorts) -> None:
        self._flows = flows
        self._ports = ports

    def execute(self, command: CashOutProfitsCommand) -> CashOutOutcome:
        flow = self._flows.get(command.flow_id)
        capital = cash_out_capital(flow.name.value, self._state_of(flow), command.capital)
        changed = flow.with_capital(capital)
        left_open = self._ports.closings.execute(CloseFlowPositionsCommand(flow, command.user_id, CloseReason.CASH_OUT))
        if left_open:
            return CashOutOutcome(flow, None, left_open)
        closed = self._state_after_closings(flow)
        cash_out_capital(flow.name.value, closed, command.capital)
        change = CapitalChange.cashed_out(closed, capital, self._ports.clock(), command.user_id)
        kept = changed if capital != closed.allocated_capital else flow
        self._flows.add_capital_change(kept, change)
        operations.info("profitti incassati", extra={"flow_id": str(flow.id.value), "freed": str(change.amount)})
        return CashOutOutcome(kept, change.amount)

    def _state_of(self, flow: Flow) -> FlowState:
        return self._ports.flow_state.execute(ReadFlowStateCommand(flow.id))

    def _state_after_closings(self, flow: Flow) -> FlowState:
        self._ports.ledger.record(flow.assigned_account_id)
        return self._state_of(flow)
