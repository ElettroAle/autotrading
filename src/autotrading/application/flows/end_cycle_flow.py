from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.read_cycle_flow import ReadCycleFlowCommand, ReadCycleFlowUseCase
from autotrading.application.flows.reconcile_account_for_cycle import (
    ReconcileAccountForCycleCommand,
    ReconcileAccountForCycleUseCase,
)
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.flow_id import FlowId


class EndCycleFlowUseCase:
    """The state of the flow at the end of the cycle, read again from the exchange after the orders (R1.7.1).

    The executions of the orders reach the ledger through the reconciliation of the account, not through the cycle.
    """

    def __init__(self, reconcile: ReconcileAccountForCycleUseCase, read_flow: ReadCycleFlowUseCase) -> None:
        self._reconcile = reconcile
        self._read_flow = read_flow

    def execute(
        self,
        flow_id: UUID,
        anchor: datetime,
        executions: Sequence[object],  # noqa: ARG002 - the signature of the port
    ) -> CycleFlow:
        self._reconcile.execute(ReconcileAccountForCycleCommand(FlowId(flow_id)))
        return self._read_flow.execute(ReadCycleFlowCommand(FlowId(flow_id), anchor, reconciled=False))
