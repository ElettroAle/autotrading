from dataclasses import dataclass

from autotrading.application.flows.ports import (
    AccountActivityPort,
    FlowLedgerPort,
    FlowRepositoryPort,
)
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.ledger import FlowTotals


@dataclass(frozen=True, slots=True)
class ReadFlowStateCommand:
    flow_id: FlowId


class ReadFlowStateUseCase:
    """A flow's positions from what the exchange shows now, its money from its ledger (R1.6.1, ADR 0063)."""

    def __init__(self, flows: FlowRepositoryPort, activity: AccountActivityPort, ledger: FlowLedgerPort) -> None:
        self._flows = flows
        self._activity = activity
        self._ledger = ledger

    def execute(self, command: ReadFlowStateCommand) -> FlowState:
        flow = self._flows.get(command.flow_id)
        activity = self._activity.execute(flow.assigned_account_id)
        totals = self._ledger.totals_of((flow.id,)).get(flow.id) or FlowTotals(flow.id)
        return FlowState.attributed(flow, activity, totals)
