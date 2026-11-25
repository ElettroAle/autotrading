from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import ColumnElement, Engine, RowMapping, Select, exists, func, select

from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import CLOSED_POSITION_PNL
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import COMPLETED
from autotrading.adapters.outbound.sqlalchemy.flow_openings import EXECUTED
from autotrading.adapters.outbound.sqlalchemy.tables import closed_positions, cycle_decisions, cycles, orders
from autotrading.adapters.outbound.sqlalchemy.time_window import within
from autotrading.domain.flows.flow_memory import OPERATIVE_ACTIONS
from autotrading.domain.flows.memory_entry import PastDecision
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.tenancy.tenant_id import TenantId

OPENINGS = frozenset({DecisionAction.OPEN, DecisionAction.REVERSE})


class _PastDecisionRow(TypedDict):
    planned_at: datetime
    asset: str
    action: str
    direction: str | None
    confidence: int | None
    reasoning: str
    price: Decimal | None
    opened_pnl: Decimal | None
    closed_pnl: Decimal | None
    opening_executed: bool


class SqlAlchemyPastDecisionsAdapter:
    """The decisions of the flows of one tenant with what came of them, under row level security (R5.3.4).

    Only the decisions of completed cycles: a cycle failed after deciding did not act on them, as in their history.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def past_decisions(self, flow_id: UUID, window: TimeWindow) -> list[PastDecision]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            rows = connection.execute(past_decisions_statement(flow_id, window)).mappings().all()
        return [past_decision_of(row) for row in rows]


def past_decisions_statement(flow_id: UUID, window: TimeWindow) -> Select[tuple[object, ...]]:
    """The operative decisions of the completed cycles of the flow in the window, newest first, each with the price of
    its last execution, the PnL of the position it opened and of the one it closed, and whether it opened one.
    """
    decision = cycle_decisions.c
    return (
        select(
            decision.planned_at,
            decision.asset,
            decision.action,
            decision.direction,
            decision.confidence,
            decision.reasoning,
            _last_execution_price().label("price"),
            _pnl_of_the_position(closed_positions.c.opening_cycle).label("opened_pnl"),
            _pnl_of_the_position(closed_positions.c.closing_cycle).label("closed_pnl"),
            exists().where(_executions_of_the_decision(), orders.c.reduce_only.is_(False)).label("opening_executed"),
        )
        .select_from(
            cycle_decisions.join(
                cycles, (decision.flow_id == cycles.c.flow_id) & (decision.planned_at == cycles.c.planned_at)
            )
        )
        .where(
            decision.flow_id == flow_id,
            cycles.c.outcome == COMPLETED,
            decision.action.in_(sorted(action.value for action in OPERATIVE_ACTIONS)),
            within(decision.planned_at, window),
        )
        .order_by(decision.planned_at.desc(), decision.position)
    )


def past_decision_of(columns: RowMapping | Mapping[str, object]) -> PastDecision:
    """An opening has the PnL of the position it opened; any other decision has the PnL of the position it closed."""
    row = cast("_PastDecisionRow", columns)
    decision = RecordedDecision.named(
        row["asset"], row["action"], row["direction"], row["confidence"], row["reasoning"]
    )
    opening = decision.action in OPENINGS
    opened_pnl = row["opened_pnl"]
    return PastDecision(
        row["planned_at"],
        decision,
        row["price"],
        opened_pnl if opening else row["closed_pnl"],
        position_open=opening and row["opening_executed"] and opened_pnl is None,
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


def _pnl_of_the_position(cycle: ColumnElement[datetime | None]) -> ColumnElement[Decimal]:
    decision = cycle_decisions.c
    return (
        select(CLOSED_POSITION_PNL)
        .where(
            closed_positions.c.flow_id == decision.flow_id,
            closed_positions.c.asset == decision.asset,
            cycle == decision.planned_at,
        )
        .limit(1)
        .scalar_subquery()
    )
