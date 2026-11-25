from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import ColumnElement, Engine, RowMapping, Select, func, select

from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import CLOSED_POSITION_PNL, close_reason_named
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import COMPLETED
from autotrading.adapters.outbound.sqlalchemy.flow_openings import EXECUTED
from autotrading.adapters.outbound.sqlalchemy.tables import closed_positions, cycle_decisions, cycles, orders
from autotrading.adapters.outbound.sqlalchemy.time_window import within
from autotrading.domain.flows.memory_entry import OPENINGS, PastDecision
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.tenancy.tenant_id import TenantId


class _PastDecisionRow(TypedDict):
    planned_at: datetime
    asset: str
    action: str
    direction: str | None
    confidence: int | None
    reasoning: str
    motive: str | None
    invalidation: str | None
    price: Decimal | None
    opened_pnl: Decimal | None
    closed_pnl: Decimal | None
    closing_reason: str | None
    position_opened_at: datetime | None
    position_closed_at: datetime | None
    opening_executed_at: datetime | None


class SqlAlchemyPastDecisionsAdapter:
    """The decisions of the flows of one tenant with what came of them, under row level security (R5.3.4, R5.3.5).

    Only the decisions of completed cycles: a cycle failed after deciding did not act on them, as in their history.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def past_decisions(
        self, flow_id: UUID, window: TimeWindow, actions: frozenset[DecisionAction]
    ) -> list[PastDecision]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            rows = connection.execute(past_decisions_statement(flow_id, window, actions)).mappings().all()
        return [past_decision_of(row) for row in rows]


def past_decisions_statement(
    flow_id: UUID, window: TimeWindow, actions: frozenset[DecisionAction]
) -> Select[tuple[object, ...]]:
    """The decisions with the actions given of the completed cycles of the flow in the window, newest first, each with
    the price of its last execution, the PnL of the position it opened and of the one it closed, how and when the
    position it opened closed, and when its opening was executed.
    """
    decision = cycle_decisions.c
    opened = closed_positions.c.opening_cycle
    return (
        select(
            decision.planned_at,
            decision.asset,
            decision.action,
            decision.direction,
            decision.confidence,
            decision.reasoning,
            decision.motive,
            decision.invalidation,
            _last_execution_price().label("price"),
            _of_the_position(CLOSED_POSITION_PNL, opened).label("opened_pnl"),
            _of_the_position(CLOSED_POSITION_PNL, closed_positions.c.closing_cycle).label("closed_pnl"),
            _of_the_position(closed_positions.c.reason, opened).label("closing_reason"),
            _of_the_position(closed_positions.c.opened_at, opened).label("position_opened_at"),
            _of_the_position(closed_positions.c.closed_at, opened).label("position_closed_at"),
            _opening_execution().label("opening_executed_at"),
        )
        .select_from(
            cycle_decisions.join(
                cycles, (decision.flow_id == cycles.c.flow_id) & (decision.planned_at == cycles.c.planned_at)
            )
        )
        .where(
            decision.flow_id == flow_id,
            cycles.c.outcome == COMPLETED,
            decision.action.in_(sorted(action.value for action in actions)),
            within(decision.planned_at, window),
        )
        .order_by(decision.planned_at.desc(), decision.position)
    )


def past_decision_of(columns: RowMapping | Mapping[str, object]) -> PastDecision:
    """An opening has the PnL of the position it opened, with how and when that position closed or, still open, since
    when; any other decision has the PnL of the position it closed.
    """
    row = cast("_PastDecisionRow", columns)
    decision = RecordedDecision.named(
        row["asset"],
        row["action"],
        row["direction"],
        row["confidence"],
        row["reasoning"],
        motive=row["motive"],
        invalidation=row["invalidation"],
    )
    if decision.action not in OPENINGS:
        return PastDecision(row["planned_at"], decision, row["price"], row["closed_pnl"])
    opened_pnl, reason = row["opened_pnl"], row["closing_reason"]
    executed_at = row["opening_executed_at"]
    return PastDecision(
        row["planned_at"],
        decision,
        row["price"],
        opened_pnl,
        position_open=executed_at is not None and opened_pnl is None,
        closed_by=None if reason is None else close_reason_named(reason),
        opened_at=row["position_opened_at"] or executed_at,
        closed_at=row["position_closed_at"],
    )


def _executions_of_the_decision() -> ColumnElement[bool]:
    decision = cycle_decisions.c
    return (
        (orders.c.flow_id == decision.flow_id)
        & (orders.c.cycle_planned_at == decision.planned_at)
        & (orders.c.decision_asset == decision.asset)
        & orders.c.status.in_(EXECUTED)
    )


def _last_execution_price() -> ColumnElement[Decimal]:
    # The opening of a reversal comes after its close: its price is the one the position of the flow started at.
    return (
        select(orders.c.average_price)
        .where(_executions_of_the_decision())
        .order_by(orders.c.executed_at.desc())
        .limit(1)
        .scalar_subquery()
    )


def _opening_execution() -> ColumnElement[datetime]:
    """When the opening of the decision was executed; none for a decision that opened nothing."""
    return (
        select(func.max(orders.c.executed_at))
        .where(_executions_of_the_decision(), orders.c.reduce_only.is_(False))
        .scalar_subquery()
    )


def _of_the_position[T](value: ColumnElement[T], cycle: ColumnElement[datetime | None]) -> ColumnElement[T]:
    """A value of the closed position of the flow on the asset of the decision opened, or closed, by its cycle."""
    decision = cycle_decisions.c
    return (
        select(value)
        .where(
            closed_positions.c.flow_id == decision.flow_id,
            closed_positions.c.asset == decision.asset,
            cycle == decision.planned_at,
        )
        .limit(1)
        .scalar_subquery()
    )
