from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import FlowSnapshot
from autotrading.application.flows.read_cycle_flow import ReadCycleFlowCommand, ReadCycleFlowUseCase
from autotrading.application.flows.reconcile_account_for_cycle import (
    ReconcileAccountForCycleCommand,
    ReconcileAccountForCycleUseCase,
)
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.flow_id import FlowId


class StartCycleFlowUseCase:
    """The state of the flow a cycle starts from, read at every cycle (R1.2.3).

    The account is reconciled first, so the ledger holds every execution the state counts (ReadCycleFlowStateUseCase).
    """

    def __init__(self, reconcile: ReconcileAccountForCycleUseCase, read_flow: ReadCycleFlowUseCase) -> None:
        self._reconcile = reconcile
        self._read_flow = read_flow

    def execute(self, flow_id: UUID, anchor: datetime) -> FlowSnapshot[CycleFlow]:
        reconciled = self._reconcile.execute(ReconcileAccountForCycleCommand(FlowId(flow_id)))
        cycle_flow = self._read_flow.execute(ReadCycleFlowCommand(FlowId(flow_id), anchor, reconciled))
        return FlowSnapshot(cycle_flow.sources, cycle_flow)
