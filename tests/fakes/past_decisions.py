"""Fake of the decisions of a flow read back with their outcome, from what the other fakes recorded, as the real adapter
reads its tables (R5.3.4)."""

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.memory_entry import PastDecision
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.orders.order import Order
from tests.fakes.closed_position_repository import ClosedPositionStore
from tests.fakes.cycles import InMemoryCycleRepositoryAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter

OPENINGS = frozenset({DecisionAction.OPEN, DecisionAction.REVERSE})


class InMemoryPastDecisionsAdapter:
    """Only the decisions of completed cycles: a cycle failed after deciding did not act on them."""

    def __init__(
        self,
        cycles: InMemoryCycleRepositoryAdapter,
        orders: InMemoryOrderRepositoryAdapter,
        closed_positions: ClosedPositionStore,
    ) -> None:
        self._cycles = cycles
        self._orders = orders
        self._closed_positions = closed_positions

    def past_decisions(self, flow_id: UUID, window: TimeWindow) -> list[PastDecision]:
        return [
            self._past(record, decision)
            for record in self._cycles.records
            if record.flow_id == flow_id
            and record.outcome is CycleOutcome.COMPLETED
            and window.contains(record.planned_at)
            for decision in record.decisions
        ]

    def _past(self, record: CycleRecord, decision: RecordedDecision) -> PastDecision:
        orders = self._executed(record.flow_id, record.planned_at, decision.asset)
        opened = self._closed(record, decision.asset, lambda position: position.opening.cycle)
        closed = self._closed(record, decision.asset, lambda position: position.closing.cycle)
        opening = decision.action in OPENINGS
        realized = opened if opening else closed
        has_opening = any(not order.request.market_order.reduce_only for order in orders)
        return PastDecision(
            record.planned_at,
            decision,
            _price_of(orders),
            None if realized is None else realized.pnl,
            position_open=opening and has_opening and opened is None,
        )

    def _executed(self, flow_id: UUID, planned_at: datetime, asset: str) -> list[Order]:
        return [
            order
            for order in self._orders.orders
            if order.execution is not None
            and (link := order.request.source.flow) is not None
            and (link.flow_id, link.cycle_planned_at, link.decision_asset) == (flow_id, planned_at, asset)
        ]

    def _closed(
        self, record: CycleRecord, asset: str, cycle_of: Callable[[ClosedPosition], datetime | None]
    ) -> ClosedPosition | None:
        return next(
            (
                position
                for position in self._closed_positions.positions
                if position.flow_id.value == record.flow_id
                and position.asset == asset
                and cycle_of(position) == record.planned_at
            ),
            None,
        )


def _price_of(orders: list[Order]) -> Decimal | None:
    """The price of the last execution of the decision: the opening of a reversal comes after its close."""
    executions = [order.execution for order in orders if order.execution is not None]
    if not executions:
        return None
    return max(executions, key=lambda execution: execution.executed_at).average_price
