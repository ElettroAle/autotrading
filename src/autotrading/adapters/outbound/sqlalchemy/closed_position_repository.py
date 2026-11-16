from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import ColumnElement, Connection, Engine, RowMapping, case, func, insert, select

from autotrading.adapters.outbound.sqlalchemy.tables import closed_positions
from autotrading.adapters.outbound.sqlalchemy.time_window import within
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.closed_position_filter import ClosedPositionFilter, PositionResult
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId

# The PnL of `ClosedPosition`: the one the exchange reported, or else the price move on the value of the margin.
_SIGN = case((closed_positions.c.side == TradeSide.LONG.value, 1), else_=-1)
_PRICE_MOVE = (closed_positions.c.close_price - closed_positions.c.open_price) / closed_positions.c.open_price
_PNL = func.coalesce(
    closed_positions.c.realized_pnl, closed_positions.c.margin * closed_positions.c.leverage * _PRICE_MOVE * _SIGN
)
_NET_PNL = _PNL - closed_positions.c.fees


class _ClosedPositionRow(TypedDict):
    tenant_id: UUID
    flow_id: UUID
    asset: str
    side: str
    leverage: int
    margin: Decimal
    open_price: Decimal
    opened_at: datetime
    opening_cycle: datetime | None
    close_price: Decimal
    closed_at: datetime
    closing_cycle: datetime | None
    fees: Decimal
    reason: str
    realized_pnl: Decimal


class SqlAlchemyClosedPositionRepositoryAdapter:
    """The closed positions of the flows of one tenant, under row level security (ADR 0047)."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def add(self, position: ClosedPosition) -> None:
        if position.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        with self._transaction() as connection:
            connection.execute(insert(closed_positions).values(row_of(position)))

    def matching(
        self, flow_id: FlowId, criteria: ClosedPositionFilter, offset: int, limit: int
    ) -> list[ClosedPosition]:
        # The identifier breaks ties of the instant, so a position never shows on two pages.
        query = (
            select(closed_positions)
            .where(closed_positions.c.flow_id == flow_id.value, matching(criteria))
            .order_by(closed_positions.c.closed_at.desc(), closed_positions.c.id)
            .offset(offset)
            .limit(limit)
        )
        with self._transaction() as connection:
            return [position_of(row) for row in connection.execute(query).mappings()]

    def count(self, flow_id: FlowId, criteria: ClosedPositionFilter) -> int:
        query = (
            select(func.count())
            .select_from(closed_positions)
            .where(closed_positions.c.flow_id == flow_id.value, matching(criteria))
        )
        with self._transaction() as connection:
            return connection.execute(query).scalar_one()

    def closed_within(self, flow_id: FlowId, window: TimeWindow) -> list[ClosedPosition]:
        query = (
            select(closed_positions)
            .where(closed_positions.c.flow_id == flow_id.value, within(closed_positions.c.closed_at, window))
            .order_by(closed_positions.c.closed_at.desc())
        )
        with self._transaction() as connection:
            return [position_of(row) for row in connection.execute(query).mappings()]

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def matching(criteria: ClosedPositionFilter) -> ColumnElement[bool]:
    """The positions that match the filter: the result goes by the PnL after the fees, as `ClosedPosition` has it."""
    condition = within(closed_positions.c.closed_at, criteria.window)
    if criteria.asset is not None:
        condition = condition & (closed_positions.c.asset == criteria.asset)
    if criteria.side is not None:
        condition = condition & (closed_positions.c.side == criteria.side.value)
    if criteria.result is PositionResult.WON:
        condition = condition & (_NET_PNL > 0)
    if criteria.result is PositionResult.LOST:
        condition = condition & (_NET_PNL < 0)
    return condition


def row_of(position: ClosedPosition) -> dict[str, object]:
    return {
        "tenant_id": position.tenant_id.value,
        "flow_id": position.flow_id.value,
        "asset": position.asset,
        "side": position.side.value,
        "leverage": position.leverage,
        "margin": position.margin,
        "open_price": position.opening.price,
        "opened_at": position.opening.at,
        "opening_cycle": position.opening.cycle,
        "close_price": position.closing.price,
        "closed_at": position.closing.at,
        "closing_cycle": position.closing.cycle,
        "fees": position.fees,
        "reason": position.reason.name.lower(),
        "realized_pnl": position.realized_pnl,
    }


def position_of(columns: RowMapping | Mapping[str, object]) -> ClosedPosition:
    row = cast("_ClosedPositionRow", columns)
    return ClosedPosition(
        tenant_id=TenantId(row["tenant_id"]),
        flow_id=FlowId(row["flow_id"]),
        asset=row["asset"],
        side=TradeSide(row["side"]),
        leverage=row["leverage"],
        margin=row["margin"],
        opening=PositionEnd(row["open_price"], row["opened_at"], row["opening_cycle"]),
        closing=PositionEnd(row["close_price"], row["closed_at"], row["closing_cycle"]),
        fees=row["fees"],
        reason=CloseReason[row["reason"].upper()],
        realized_pnl=row["realized_pnl"],
    )
