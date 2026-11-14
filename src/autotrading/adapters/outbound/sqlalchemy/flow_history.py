from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Connection,
    Engine,
    RowMapping,
    Select,
    func,
    literal,
    select,
    tuple_,
    type_coerce,
)
from sqlalchemy.dialects.postgresql import JSONB

from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import position_of
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import RECORDED, record_of
from autotrading.adapters.outbound.sqlalchemy.tables import (
    account_fills,
    accounts,
    closed_positions,
    cycles,
    flow_versions,
    flows,
    orders,
)
from autotrading.adapters.outbound.sqlalchemy.time_window import within
from autotrading.domain.flows.history import (
    ClosedPositionHistoryEntry,
    CycleHistoryEntry,
    HistoryCursor,
    HistoryQuery,
    OrderExecution,
    OrderHistoryEntry,
)
from autotrading.domain.orders.order import OrderOrigin, OrderStatus
from autotrading.domain.tenancy.tenant_id import TenantId

type Row = RowMapping | Mapping[str, object]


class _CycleEntryRow(TypedDict):
    flow_name: str
    version: int | None


class _PositionEntryRow(TypedDict):
    id: UUID
    flow_name: str


class _FillRow(TypedDict):
    order_id: UUID
    executed_at: datetime
    price: Decimal
    size: Decimal
    fee: Decimal


class _OrderRow(TypedDict):
    id: UUID
    created_at: datetime
    account_id: UUID
    account_name: str
    flow_id: UUID | None
    flow_name: str | None
    coin: str
    direction: str
    reduce_only: bool
    leverage: int
    requested_size: Decimal
    status: str
    origin: str


class SqlAlchemyFlowHistoryAdapter:
    """The histories of the flows of one tenant, under row level security (R2.5.1, ADR 0138).

    The pages go by keyset on instant and key, newest first, as the operations do: a page costs the same however deep
    it is, and the indexes on tenant, flow and instant serve it. A configuration version is in force from the instant
    it was saved until the next one of its flow.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def cycles(self, query: HistoryQuery) -> list[CycleHistoryEntry]:
        with self._transaction() as connection:
            rows = connection.execute(cycles_statement(query)).mappings().all()
        return [cycle_entry_of(row) for row in rows]

    def closed_positions(self, query: HistoryQuery) -> list[ClosedPositionHistoryEntry]:
        with self._transaction() as connection:
            rows = connection.execute(closed_positions_statement(query)).mappings().all()
        return [position_entry_of(row) for row in rows]

    def orders(self, query: HistoryQuery) -> list[OrderHistoryEntry]:
        with self._transaction() as connection:
            rows = connection.execute(orders_statement(query)).mappings().all()
            order_ids = [row["id"] for row in rows]
            fills = connection.execute(executions_statement(order_ids)).mappings().all() if order_ids else []
        executions = executions_by_order(fills)
        return [order_entry_of(row, executions[row["id"]]) for row in rows]

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def cycles_statement(query: HistoryQuery) -> Select[tuple[object, ...]]:
    """The cycles of the page; the version is the one in force when the cycle started, or was planned if it never did,
    as a cycle reads its configuration at its start.
    """
    criteria, columns = query.criteria, cycles.c
    started = func.coalesce(columns.started_at, columns.planned_at)
    version = _version_in_force(columns.flow_id, started)
    filters = [RECORDED, within(columns.planned_at, query.window), *_after(columns.planned_at, columns.flow_id, query)]
    if criteria.flow_id is not None:
        filters.append(columns.flow_id == criteria.flow_id)
    if criteria.account_id is not None:
        filters.append(flows.c.account_id == criteria.account_id)
    if criteria.version is not None:
        filters.append(version == criteria.version)
    if criteria.asset is not None:
        filters.append(_assets_in_force(columns.flow_id, started).has_key(criteria.asset))
    return (
        select(cycles, flows.c.name.label("flow_name"), version.label("version"))
        .join(flows, flows.c.id == columns.flow_id)
        .where(*filters)
        .order_by(columns.planned_at.desc(), columns.flow_id.desc())
        .limit(query.limit + 1)
    )


def closed_positions_statement(query: HistoryQuery) -> Select[tuple[object, ...]]:
    """The closed positions of the page: period and version go by the closing instant."""
    criteria, columns = query.criteria, closed_positions.c
    filters = [within(columns.closed_at, query.window), *_after(columns.closed_at, columns.id, query)]
    if criteria.flow_id is not None:
        filters.append(columns.flow_id == criteria.flow_id)
    if criteria.account_id is not None:
        filters.append(flows.c.account_id == criteria.account_id)
    if criteria.asset is not None:
        filters.append(columns.asset == criteria.asset)
    if criteria.version is not None:
        filters.append(_version_in_force(columns.flow_id, columns.closed_at) == criteria.version)
    return (
        select(closed_positions, flows.c.name.label("flow_name"))
        .join(flows, flows.c.id == columns.flow_id)
        .where(*filters)
        .order_by(columns.closed_at.desc(), columns.id.desc())
        .limit(query.limit + 1)
    )


def orders_statement(query: HistoryQuery) -> Select[tuple[object, ...]]:
    """The orders of the page: period and version go by the creation instant; an order of no flow has no version."""
    criteria, columns = query.criteria, orders.c
    filters = [within(columns.created_at, query.window), *_after(columns.created_at, columns.id, query)]
    if criteria.flow_id is not None:
        filters.append(columns.flow_id == criteria.flow_id)
    if criteria.account_id is not None:
        filters.append(columns.account_id == criteria.account_id)
    if criteria.asset is not None:
        filters.append(columns.coin == criteria.asset)
    if criteria.version is not None:
        filters.append(_version_in_force(columns.flow_id, columns.created_at) == criteria.version)
    return (
        select(orders, accounts.c.name.label("account_name"), flows.c.name.label("flow_name"))
        .select_from(
            orders.join(accounts, accounts.c.id == columns.account_id).outerjoin(flows, flows.c.id == columns.flow_id)
        )
        .where(*filters)
        .order_by(columns.created_at.desc(), columns.id.desc())
        .limit(query.limit + 1)
    )


def executions_statement(order_ids: Sequence[UUID]) -> Select[tuple[object, ...]]:
    """The executions the ledger recorded for the orders, oldest first."""
    return (
        select(account_fills)
        .where(account_fills.c.order_id.in_(order_ids))
        .order_by(account_fills.c.executed_at, account_fills.c.id)
    )


def cycle_entry_of(columns: Row) -> CycleHistoryEntry:
    row = cast("_CycleEntryRow", columns)
    return CycleHistoryEntry(row["flow_name"], row["version"], record_of(columns))


def position_entry_of(columns: Row) -> ClosedPositionHistoryEntry:
    row = cast("_PositionEntryRow", columns)
    return ClosedPositionHistoryEntry(row["id"], row["flow_name"], position_of(columns))


def executions_by_order(fills: Iterable[Row]) -> defaultdict[UUID, list[OrderExecution]]:
    found: defaultdict[UUID, list[OrderExecution]] = defaultdict(list)
    for columns in fills:
        fill = cast("_FillRow", columns)
        found[fill["order_id"]].append(OrderExecution(fill["executed_at"], fill["price"], fill["size"], fill["fee"]))
    return found


def order_entry_of(columns: Row, executions: Sequence[OrderExecution]) -> OrderHistoryEntry:
    row = cast("_OrderRow", columns)
    return OrderHistoryEntry(
        order_id=row["id"],
        created_at=row["created_at"],
        account_id=row["account_id"],
        account_name=row["account_name"],
        flow_id=row["flow_id"],
        flow_name=row["flow_name"],
        asset=row["coin"],
        direction=row["direction"],
        closing=row["reduce_only"],
        leverage=row["leverage"],
        requested_size=row["requested_size"],
        status=OrderStatus[row["status"]].value,
        origin=OrderOrigin[row["origin"]].value,
        executions=tuple(executions),
    )


def _version_in_force(flow_id: ColumnElement[UUID], instant: ColumnElement[datetime]) -> ColumnElement[int]:
    return (
        select(func.max(flow_versions.c.version))
        .where(flow_versions.c.flow_id == flow_id, flow_versions.c.created_at <= instant)
        .scalar_subquery()
    )


def _assets_in_force(flow_id: ColumnElement[UUID], instant: ColumnElement[datetime]) -> ColumnElement[object]:
    """The assets of the configuration version in force at the instant, as JSONB."""
    in_force = (
        select(flow_versions.c.configuration.cast(JSONB)["assets"])
        .where(flow_versions.c.flow_id == flow_id, flow_versions.c.created_at <= instant)
        .order_by(flow_versions.c.version.desc())
        .limit(1)
        .scalar_subquery()
    )
    return type_coerce(in_force, JSONB)


def _after(
    instant: ColumnElement[datetime], key: ColumnElement[UUID], query: HistoryQuery
) -> list[ColumnElement[bool]]:
    cursor: HistoryCursor | None = query.after
    if cursor is None:
        return []
    return [tuple_(instant, key) < tuple_(literal(cursor.at), literal(cursor.key))]
