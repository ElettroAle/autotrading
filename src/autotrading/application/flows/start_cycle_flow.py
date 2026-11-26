from dataclasses import replace
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import FlowSnapshot
from autotrading.application.flows.read_cycle_flow import ReadCycleFlowCommand, ReadCycleFlowUseCase
from autotrading.application.flows.read_round_trip_cost import ReadRoundTripCostUseCase
from autotrading.application.flows.reconcile_account_for_cycle import (
    ReconcileAccountForCycleCommand,
    ReconcileAccountForCycleUseCase,
)
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.flow_id import FlowId


class StartCycleFlowUseCase:
    """The state of the flow a cycle starts from, read at every cycle (R1.2.3).

    The account is reconciled first, so the ledger holds every execution the state counts (ReadCycleFlowStateUseCase).
    The fee of the account for the agent is read here, once for the cycle, with the option of the flow on (R5.5.6).
    """

    def __init__(
        self,
        reconcile: ReconcileAccountForCycleUseCase,
        read_flow: ReadCycleFlowUseCase,
        read_round_trip_cost: ReadRoundTripCostUseCase,
    ) -> None:
        self._reconcile = reconcile
        self._read_flow = read_flow
        self._read_round_trip_cost = read_round_trip_cost

    def execute(self, flow_id: UUID, anchor: datetime) -> FlowSnapshot[CycleFlow]:
        reconciled = self._reconcile.execute(ReconcileAccountForCycleCommand(FlowId(flow_id)))
        cycle_flow = self._read_flow.execute(ReadCycleFlowCommand(FlowId(flow_id), anchor, reconciled))
        round_trip_cost = self._read_round_trip_cost.execute(cycle_flow.flow)
        return FlowSnapshot(cycle_flow.sources, replace(cycle_flow, round_trip_cost=round_trip_cost))
