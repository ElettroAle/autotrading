from collections.abc import Iterator
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Connection,
    Engine,
    Numeric,
    RowMapping,
    Select,
    Subquery,
    Text,
    and_,
    func,
    literal,
    null,
    select,
    tuple_,
    union_all,
)

from autotrading.adapters.outbound.sqlalchemy.tables import account_fills, account_funding, accounts, flows
from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.domain.flows.ledger import ZERO
from autotrading.domain.flows.operations import (
    FUNDING,
    AccountOperations,
    AccountScope,
    FlowOperations,
    Operation,
    OperationCursor,
    OperationSource,
    OperationsOwner,
    OperationsPage,
    OperationsQuery,
    OperationsReport,
    OperationsTotals,
)
from autotrading.domain.tenancy.tenant_id import TenantId

# Rows fetched from the server-side cursor at a time: the export never holds the whole ledger in memory.
EXPORT_BATCH = 500


class SqlAlchemyFlowOperationsAdapter:
    """The ledger read by its owner (ADR 0074, ADR 0080).

    The pages go by keyset on instant, source and row: no offset, so a page costs the same however deep it is, and the
    indexes on tenant, flow or account and instant serve it. The totals are one aggregate over the same filters, and
    the export reads a server-side cursor in batches.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def report(self, owner: OperationsOwner, query: OperationsQuery) -> OperationsReport:
        rows = _rows(owner)
        with self._engine.begin() as connection:
            self._bind_tenant(connection)
            self._check_account(connection, owner)
            found = connection.execute(_newest_first(rows, query)).mappings().all()
            totals = connection.execute(_totals(rows, query.unpaged())).mappings().one()
        page = OperationsPage.of([_operation_of(row) for row in found], query.limit)
        sums = OperationsTotals(totals["count"], totals["realized_pnl"], totals["fees"], totals["funding"])
        return OperationsReport(page, sums)

    def export(self, owner: OperationsOwner, query: OperationsQuery) -> Iterator[Operation]:
        with self._engine.begin() as connection:
            self._bind_tenant(connection)
            self._check_account(connection, owner)
        return self._streamed(owner, query.unpaged())

    def _streamed(self, owner: OperationsOwner, query: OperationsQuery) -> Iterator[Operation]:
        statement = _oldest_first(_rows(owner), query).execution_options(yield_per=EXPORT_BATCH)
        with self._engine.begin() as connection:
            self._bind_tenant(connection)
            for row in connection.execute(statement).mappings():
                yield _operation_of(row)

    def _bind_tenant(self, connection: Connection) -> None:
        # Local to the transaction: a pooled connection never carries the tenant of a previous request.
        connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))

    @staticmethod
    def _check_account(connection: Connection, owner: OperationsOwner) -> None:
        if not isinstance(owner, AccountOperations):
            return
        visible = connection.execute(select(accounts.c.id).where(accounts.c.id == owner.account_id)).first()
        if visible is None:
            raise FlowAccountNotFoundError


def _rows(owner: OperationsOwner) -> Subquery:
    executions, funding = _owned_by(owner)
    of_executions = select(
        account_fills.c.executed_at.label("occurred_at"),
        literal(int(OperationSource.EXECUTION)).label("source"),
        account_fills.c.id.label("row_id"),
        account_fills.c.flow_id,
        account_fills.c.asset,
        account_fills.c.kind,
        account_fills.c.size,
        account_fills.c.price,
        account_fills.c.fee,
        account_fills.c.realized_pnl,
        literal(ZERO, Numeric).label("funding"),
    ).where(executions)
    of_funding = select(
        account_funding.c.paid_at,
        literal(int(OperationSource.FUNDING)),
        account_funding.c.id,
        account_funding.c.flow_id,
        account_funding.c.asset,
        literal(FUNDING, Text),
        null().cast(Numeric),
        null().cast(Numeric),
        literal(ZERO, Numeric),
        literal(ZERO, Numeric),
        account_funding.c.amount,
    ).where(funding)
    return union_all(of_executions, of_funding).subquery()


def _owned_by(owner: OperationsOwner) -> tuple[ColumnElement[bool], ColumnElement[bool]]:
    if isinstance(owner, FlowOperations):
        return account_fills.c.flow_id == owner.flow_id.value, account_funding.c.flow_id == owner.flow_id.value
    return _of_account(owner.account_id, owner.scope)


def _of_account(account_id: UUID, scope: AccountScope) -> tuple[ColumnElement[bool], ColumnElement[bool]]:
    executions, funding = account_fills.c.account_id == account_id, account_funding.c.account_id == account_id
    if scope is AccountScope.ALL:
        return executions, funding
    return and_(executions, account_fills.c.flow_id.is_(None)), and_(funding, account_funding.c.flow_id.is_(None))


def _named(rows: Subquery, query: OperationsQuery) -> Select[tuple[object, ...]]:
    return (
        select(rows, flows.c.name.label("flow_name"))
        .select_from(rows.outerjoin(flows, flows.c.id == rows.c.flow_id))
        .where(*_filters(rows, query))
    )


def _newest_first(rows: Subquery, query: OperationsQuery) -> Select[tuple[object, ...]]:
    order = (rows.c.occurred_at.desc(), rows.c.source.desc(), rows.c.row_id.desc())
    return _named(rows, query).order_by(*order).limit(query.limit + 1)


def _oldest_first(rows: Subquery, query: OperationsQuery) -> Select[tuple[object, ...]]:
    return _named(rows, query).order_by(rows.c.occurred_at, rows.c.source, rows.c.row_id)


def _totals(rows: Subquery, query: OperationsQuery) -> Select[tuple[object, ...]]:
    return select(
        func.count().label("count"),
        func.coalesce(func.sum(rows.c.realized_pnl), ZERO).label("realized_pnl"),
        func.coalesce(func.sum(rows.c.fee), ZERO).label("fees"),
        func.coalesce(func.sum(rows.c.funding), ZERO).label("funding"),
    ).where(*_filters(rows, query))


def _filters(rows: Subquery, query: OperationsQuery) -> list[ColumnElement[bool]]:
    columns = rows.c
    filters: list[ColumnElement[bool]] = []
    if query.asset is not None:
        filters.append(columns.asset == query.asset)
    if query.since is not None:
        filters.append(columns.occurred_at >= query.since)
    if query.until is not None:
        filters.append(columns.occurred_at < query.until)
    if query.after is not None:
        after = query.after
        filters.append(
            tuple_(columns.occurred_at, columns.source, columns.row_id)
            < tuple_(literal(after.occurred_at), literal(int(after.source)), literal(after.row_id))
        )
    return filters


def _operation_of(values: RowMapping) -> Operation:
    return Operation(
        cursor=OperationCursor(values["occurred_at"], OperationSource(values["source"]), values["row_id"]),
        asset=values["asset"],
        kind=values["kind"],
        size=values["size"],
        price=values["price"],
        fee=values["fee"],
        realized_pnl=values["realized_pnl"],
        funding=values["funding"],
        flow=values["flow_name"],
    )
