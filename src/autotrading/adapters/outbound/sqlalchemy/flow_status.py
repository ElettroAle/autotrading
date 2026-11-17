from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import Connection, Engine, Numeric, RowMapping, Select, func, select
from sqlalchemy.exc import SQLAlchemyError

from autotrading.adapters.outbound.sqlalchemy.tables import (
    equity_snapshots,
    flow_capital_changes,
    flow_position_totals,
    flows,
)
from autotrading.application.notifications.errors import FlowStatusUnavailableError
from autotrading.domain.notifications.flow_status import FlowStatusFigures, NotifiedFlowStatus, RecordedEquity
from autotrading.domain.tenancy.tenant_id import TenantId

ARCHIVED = "archived"


class _FlowRow(TypedDict):
    id: UUID
    status: str


class _EquityRow(TypedDict):
    planned_at: datetime
    equity: Decimal
    allocated_capital: Decimal


class SqlAlchemyFlowStatusAdapter:
    """The state of the flows of one tenant as their last cycle recorded it, read under row level security for the
    notifications (ADR stato-del-flusso-in-ogni-notifica).
    """

    def __init__(self, engine: Engine, tenant_id: TenantId, currency: str) -> None:
        self._engine = engine
        self._tenant_id = tenant_id
        self._currency = currency

    def status_of(self, flow_name: str) -> FlowStatusFigures | None:
        try:
            with self._transaction() as connection:
                return self._figures(connection, flow_name)
        except SQLAlchemyError as error:
            raise FlowStatusUnavailableError from error

    def _figures(self, connection: Connection, flow_name: str) -> FlowStatusFigures | None:
        flow = connection.execute(flow_query(flow_name)).mappings().first()
        if flow is None:
            return None
        flow_id = cast("_FlowRow", flow)["id"]
        equity = connection.execute(last_equity_query(flow_id)).mappings().first()
        open_positions = connection.execute(open_positions_query(flow_id)).scalar_one()
        recorded = None if equity is None else recorded_of(equity, _cashed_out(connection, flow_id, equity))
        return figures_of(flow, open_positions, self._currency, recorded)

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _cashed_out(connection: Connection, flow_id: UUID, equity: RowMapping) -> Decimal:
    planned_at = cast("_EquityRow", equity)["planned_at"]
    return connection.execute(cashed_out_query(flow_id, planned_at)).scalar_one()


def flow_query(flow_name: str) -> Select[tuple[object, ...]]:
    """The flow not archived with the name: the name is unique among them (ADR 0031)."""
    return select(flows.c.id, flows.c.status).where(flows.c.name == flow_name, flows.c.status != ARCHIVED)


def last_equity_query(flow_id: UUID) -> Select[tuple[object, ...]]:
    return (
        select(equity_snapshots.c.planned_at, equity_snapshots.c.equity, equity_snapshots.c.allocated_capital)
        .where(equity_snapshots.c.flow_id == flow_id)
        .order_by(equity_snapshots.c.planned_at.desc())
        .limit(1)
    )


def cashed_out_query(flow_id: UUID, until: datetime) -> Select[Decimal]:
    """The profits cashed out up to the cycle the equity was recorded at: the same ones the equity left out."""
    cashed_out = func.coalesce(func.sum(flow_capital_changes.c.cashed_profit), 0, type_=Numeric)
    return select(cashed_out).where(
        flow_capital_changes.c.flow_id == flow_id, flow_capital_changes.c.changed_at <= until
    )


def open_positions_query(flow_id: UUID) -> Select[int]:
    """The positions the ledger expects the flow to hold (ADR 0063)."""
    return select(func.count()).where(flow_position_totals.c.flow_id == flow_id, flow_position_totals.c.size != 0)


def recorded_of(columns: RowMapping | Mapping[str, object], cashed_out: Decimal) -> RecordedEquity:
    row = cast("_EquityRow", columns)
    return RecordedEquity(row["equity"], row["allocated_capital"], cashed_out)


def figures_of(
    flow: RowMapping | Mapping[str, object], open_positions: int, currency: str, recorded: RecordedEquity | None
) -> FlowStatusFigures:
    status = NotifiedFlowStatus[cast("_FlowRow", flow)["status"].upper()]
    return FlowStatusFigures(status, open_positions, currency, recorded)
