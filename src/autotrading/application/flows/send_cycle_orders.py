from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import CycleOrderExecutionPort, ExitPlanRepositoryPort, FlowOpeningsPort
from autotrading.domain.flows.cycle_order import CycleOrder, CycleOrders
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.risk_outcome import ApprovedOpening


class SendCycleOrdersUseCase:
    """Hands the approved orders of a cycle to the execution, on the account of the flow (R1.5.5), then puts in force
    the exit plan of every opening the exchange executed in the cycle (R3.1.1).
    """

    def __init__(
        self,
        execution: CycleOrderExecutionPort,
        openings: FlowOpeningsPort,
        exit_plans: ExitPlanRepositoryPort,
    ) -> None:
        self._execution = execution
        self._openings = openings
        self._exit_plans = exit_plans

    def execute(self, flow_id: UUID, planned_at: datetime, orders: Sequence[CycleOrder]) -> Sequence[object]:
        approved = tuple(orders)
        if not approved:
            return ()
        flow = approved[0].flow.flow
        cycle = CycleOrders(
            flow.assigned_account_id, flow_id, flow.name.value, planned_at, tuple(order.outcome for order in approved)
        )
        sent = self._execution.execute(cycle)
        self._keep_exit_plans(cycle)
        return sent

    def _keep_exit_plans(self, cycle: CycleOrders) -> None:
        flow_id = FlowId(cycle.flow_id)
        for opening in (order for order in cycle.orders if isinstance(order, ApprovedOpening)):
            if self._executed_in(cycle, flow_id, opening.asset):
                self._exit_plans.save(flow_id, opening.asset, opening.exit_plan)

    def _executed_in(self, cycle: CycleOrders, flow_id: FlowId, asset: str) -> bool:
        """The last executed opening of the flow on the asset is the one this cycle sent."""
        last = self._openings.last_opening(flow_id, asset)
        return last is not None and last.end.cycle == cycle.planned_at
