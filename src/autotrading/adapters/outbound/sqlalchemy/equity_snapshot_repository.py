from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import Connection, Engine, RowMapping, Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.tables import equity_snapshots
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.loss_guard import LossReferences
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.tenancy.tenant_id import TenantId

KEY = ["flow_id", "planned_at"]


class _EquityRow(TypedDict):
    flow_id: UUID
    planned_at: datetime
    allocated_capital: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    fees: Decimal
    funding: Decimal


class SqlAlchemyEquitySnapshotRepositoryAdapter:
    """The equity of the cycles of the flows of one tenant, recorded and read under row level security (ADR 0120), and
    the references the losses of a flow are measured from (R3.2.2).
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def record(self, snapshot: EquitySnapshot) -> None:
        # A cycle resumed from its checkpoint closes again: its first equity stays (ADR 0104).
        statement = (
            insert(equity_snapshots)
            .values(row_of(snapshot, self._tenant_id))
            .on_conflict_do_nothing(index_elements=KEY)
        )
        try:
            with self._transaction() as connection:
                connection.execute(statement)
        except IntegrityError as error:
            # The key (flow_id, tenant_id) of the flow admits only a flow of the tenant of the adapter.
            raise CrossTenantAccessError from error

    def of_flow(self, flow_id: UUID, window: TimeWindow) -> list[EquitySnapshot]:
        with self._transaction() as connection:
            return [snapshot_of(row) for row in connection.execute(of_flow_query(flow_id, window)).mappings()]

    def loss_references(self, flow_id: UUID, day_start: datetime, peak_since: datetime) -> LossReferences:
        with self._transaction() as connection:
            daily = _first(connection, daily_until_query(flow_id, day_start)) or _first(
                connection, daily_from_query(flow_id, day_start)
            )
            return LossReferences(daily, _first(connection, peak_query(flow_id, peak_since)))

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def of_flow_query(flow_id: UUID, window: TimeWindow) -> Select[tuple[object, ...]]:
    query = select(equity_snapshots).where(equity_snapshots.c.flow_id == flow_id)
    if window.since is not None:
        query = query.where(equity_snapshots.c.planned_at >= window.since)
    if window.until is not None:
        query = query.where(equity_snapshots.c.planned_at < window.until)
    return query.order_by(equity_snapshots.c.planned_at)


def daily_until_query(flow_id: UUID, day_start: datetime) -> Select[tuple[object, ...]]:
    """The last equity of the flow recorded at the start of the day or before (R3.2.2)."""
    return (
        select(equity_snapshots)
        .where(equity_snapshots.c.flow_id == flow_id, equity_snapshots.c.planned_at <= day_start)
        .order_by(equity_snapshots.c.planned_at.desc())
        .limit(1)
    )


def daily_from_query(flow_id: UUID, day_start: datetime) -> Select[tuple[object, ...]]:
    """The first equity of the day, for a flow without equity before it (R3.2.2)."""
    return (
        select(equity_snapshots)
        .where(equity_snapshots.c.flow_id == flow_id, equity_snapshots.c.planned_at >= day_start)
        .order_by(equity_snapshots.c.planned_at)
        .limit(1)
    )


def peak_query(flow_id: UUID, since: datetime) -> Select[tuple[object, ...]]:
    """The equity highest once brought to the capital of now since the instant: the highest gain on its capital, so a
    change of capital moves no reference (R3.2.2).
    """
    return (
        select(equity_snapshots)
        .where(equity_snapshots.c.flow_id == flow_id, equity_snapshots.c.planned_at >= since)
        .order_by(
            (equity_snapshots.c.equity - equity_snapshots.c.allocated_capital).desc(),
            equity_snapshots.c.planned_at.desc(),
        )
        .limit(1)
    )


def _first(connection: Connection, query: Select[tuple[object, ...]]) -> EquitySnapshot | None:
    row = connection.execute(query).mappings().first()
    return None if row is None else snapshot_of(row)


def row_of(snapshot: EquitySnapshot, tenant_id: TenantId) -> dict[str, object]:
    return {
        "tenant_id": tenant_id.value,
        "flow_id": snapshot.flow_id,
        "planned_at": snapshot.planned_at,
        # Kept beside its parts, so the ranking and the curves read it without computing it again (R2.4.2).
        "equity": snapshot.equity,
        "allocated_capital": snapshot.allocated_capital,
        "realized_pnl": snapshot.realized_pnl,
        "unrealized_pnl": snapshot.unrealized_pnl,
        "fees": snapshot.fees,
        "funding": snapshot.funding,
    }


def snapshot_of(columns: RowMapping | Mapping[str, object]) -> EquitySnapshot:
    row = cast("_EquityRow", columns)
    return EquitySnapshot(
        flow_id=row["flow_id"],
        planned_at=row["planned_at"],
        allocated_capital=row["allocated_capital"],
        realized_pnl=row["realized_pnl"],
        unrealized_pnl=row["unrealized_pnl"],
        fees=row["fees"],
        funding=row["funding"],
    )
