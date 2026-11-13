from dataclasses import dataclass

from autotrading.application.flows.errors import FlowExchangeUnavailableError, FlowPositionMismatchError
from autotrading.application.flows.read_flow_state import ReadFlowStateCommand, ReadFlowStateUseCase
from autotrading.application.flows.reconcile_account_for_cycle import (
    ReconcileAccountForCycleCommand,
    ReconcileAccountForCycleUseCase,
)
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState


@dataclass(frozen=True, slots=True)
class ReadCycleFlowStateCommand:
    """The flow at the start of its cycle, and whether its account was just reconciled."""

    flow_id: FlowId
    reconciled: bool


class ReadCycleFlowStateUseCase:
    """The state of the flow a cycle starts from: a flow whose position on the exchange is not the one its ledger
    expects sends no order (Bug 155, ADR 0064).

    Without a reconciliation the ledger may lag behind the exchange, so the comparison waits for the next cycle. The
    flow pauses only for a difference the executions published meanwhile do not explain: the account is reconciled
    once more and the positions compared again (Bug 165, ADR 0075). If the executions cannot be read again the cycle
    fails without pausing the flow, and the next cycle compares them.
    """

    def __init__(self, read_flow_state: ReadFlowStateUseCase, reconcile: ReconcileAccountForCycleUseCase) -> None:
        self._read_flow_state = read_flow_state
        self._reconcile = reconcile

    def execute(self, command: ReadCycleFlowStateCommand) -> FlowState:
        state = self._read_flow_state.execute(ReadFlowStateCommand(command.flow_id))
        if not command.reconciled or state.position_mismatch() is None:
            return state
        return self._compared_again(command.flow_id)

    def _compared_again(self, flow_id: FlowId) -> FlowState:
        if not self._reconcile.execute(ReconcileAccountForCycleCommand(flow_id)):
            raise FlowExchangeUnavailableError
        state = self._read_flow_state.execute(ReadFlowStateCommand(flow_id))
        mismatch = state.position_mismatch()
        if mismatch is not None:
            raise FlowPositionMismatchError(mismatch)
        return state
