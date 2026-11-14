from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import CycleOrderExecutionPort
from autotrading.domain.flows.cycle_order import CycleOrder, CycleOrders


class SendCycleOrdersUseCase:
    """Hands the approved orders of a cycle to the execution, on the account of the flow (R1.5.5)."""

    def __init__(self, execution: CycleOrderExecutionPort) -> None:
        self._execution = execution

    def execute(self, flow_id: UUID, planned_at: datetime, orders: Sequence[CycleOrder]) -> Sequence[object]:
        approved = tuple(orders)
        if not approved:
            return ()
        flow = approved[0].flow.flow
        cycle = CycleOrders(
            flow.assigned_account_id, flow_id, flow.name.value, planned_at, tuple(order.outcome for order in approved)
        )
        return self._execution.execute(cycle)
