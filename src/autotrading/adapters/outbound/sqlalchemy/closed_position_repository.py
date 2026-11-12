from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Connection, Engine, RowMapping, func, insert, select

from autotrading.adapters.outbound.sqlalchemy.tables import closed_positions
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId


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

    def of_flow(self, flow_id: FlowId) -> list[ClosedPosition]:
        query = (
            select(closed_positions)
            .where(closed_positions.c.flow_id == flow_id.value)
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


def position_of(row: RowMapping | Mapping[str, Any]) -> ClosedPosition:
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
