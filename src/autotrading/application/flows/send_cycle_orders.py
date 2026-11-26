from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import (
    CycleOrderExecutionPort,
    FlowOpeningsPort,
    FlowRepositoryPort,
    OpenPositionRecords,
)
from autotrading.domain.flows.cycle_order import CycleOrder, CycleOrders
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.risk_outcome import ApprovedOpening, ApprovedUpdate
from autotrading.domain.flows.watched_position import TrailingStopNote


class SendCycleOrdersUseCase:
    """Hands the approved orders of a cycle to the execution, on the account of the flow (R1.5.5), with the exit plan of
    every opening in force while the exchange executes it (R3.1.1).

    The plan of an opening the exchange did not execute is removed after; the plan of a position closed during the
    execution, because the exchange refused its stop loss, is removed by its closing (R3.1.2). The execution runs even
    without orders: a position of the flow without a stop loss gets the default one at every cycle, with the defaults of
    the version in force (R3.1.2). After an update the plan in force holds the levels the exchange has waiting, never
    those it refused (R3.1.3). A move of the stop that follows the price the exchange refused since the previous cycle
    is recorded once, beside the notes of the protections (R5.5.1).
    """

    def __init__(
        self,
        execution: CycleOrderExecutionPort,
        openings: FlowOpeningsPort,
        flows: FlowRepositoryPort,
        records: OpenPositionRecords,
    ) -> None:
        self._execution = execution
        self._openings = openings
        self._flows = flows
        self._exit_plans = records.exit_plans
        self._protection_levels = records.protection_levels
        self._watched = records.watched

    def execute(self, flow_id: UUID, planned_at: datetime, orders: Sequence[CycleOrder]) -> Sequence[object]:
        cycle = self._cycle_of(FlowId(flow_id), planned_at, orders)
        openings = tuple(order for order in cycle.orders if isinstance(order, ApprovedOpening))
        for opening in openings:
            self._exit_plans.save(FlowId(flow_id), opening.asset, opening.exit_plan)
        sent = self._execution.execute(cycle)
        for opening in openings:
            if not self._executed_in(cycle, opening.asset):
                self._exit_plans.remove(FlowId(flow_id), opening.asset)
        for update in (order for order in cycle.orders if isinstance(order, ApprovedUpdate)):
            self._put_in_force(FlowId(flow_id), update)
        return (*sent, *self._refused_stop_moves(FlowId(flow_id)))

    def _refused_stop_moves(self, flow_id: FlowId) -> list[TrailingStopNote]:
        notes: list[TrailingStopNote] = []
        for position in self._watched.watched_of(flow_id):
            note = position.note()
            if note is None:
                continue
            self._watched.save(flow_id, position.told())
            notes.append(note)
        return notes

    def _put_in_force(self, flow_id: FlowId, update: ApprovedUpdate) -> None:
        current = self._exit_plans.current(flow_id, update.asset) or ExitPlan()
        placed = self._protection_levels.placed_levels(flow_id, update.asset)
        self._exit_plans.save(flow_id, update.asset, current.updated(update.plan_change, placed))

    def _cycle_of(self, flow_id: FlowId, planned_at: datetime, orders: Sequence[CycleOrder]) -> CycleOrders:
        # The version the cycle read at its start, which its orders carry; without orders, the one in force.
        flow = orders[0].flow.flow if orders else self._flows.get(flow_id)
        configuration = flow.configuration
        defaults = configuration.protection_defaults
        return CycleOrders(
            flow.assigned_account_id,
            flow_id.value,
            flow.name.value,
            planned_at,
            tuple(order.outcome for order in orders),
            configuration.assets,
            defaults.stop_loss_percent,
            defaults.take_profit_percent,
        )

    def _executed_in(self, cycle: CycleOrders, asset: str) -> bool:
        """The last executed opening of the flow on the asset is the one this cycle sent."""
        last = self._openings.last_opening(FlowId(cycle.flow_id), asset)
        return last is not None and last.end.cycle == cycle.planned_at
