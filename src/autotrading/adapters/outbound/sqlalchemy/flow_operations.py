from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    CompoundSelect,
    Engine,
    Numeric,
    RowMapping,
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

from autotrading.adapters.outbound.sqlalchemy.tables import account_fills, account_funding, accounts
from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import ZERO
from autotrading.domain.flows.operations import (
    FUNDING,
    Operation,
    OperationCursor,
    OperationSource,
    OperationsPage,
    OperationsQuery,
)
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyFlowOperationsAdapter:
    """The ledger read by its owner, a page at a time, newest first (ADR 0072).

    The pages go by keyset on instant, source and row: no offset, so a page costs the same however deep it is, and the
    indexes on tenant, flow or account and instant serve it.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def of_flow(self, flow_id: FlowId, query: OperationsQuery) -> OperationsPage:
        return self._page(account_fills.c.flow_id == flow_id.value, account_funding.c.flow_id == flow_id.value, query)

    def unattributed_of_account(self, account_id: UUID, query: OperationsQuery) -> OperationsPage:
        with self._engine.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            visible = connection.execute(select(accounts.c.id).where(accounts.c.id == account_id)).first()
        if visible is None:
            raise FlowAccountNotFoundError
        return self._page(
            and_(account_fills.c.account_id == account_id, account_fills.c.flow_id.is_(None)),
            and_(account_funding.c.account_id == account_id, account_funding.c.flow_id.is_(None)),
            query,
        )

    def _page(
        self, executions: ColumnElement[bool], funding: ColumnElement[bool], query: OperationsQuery
    ) -> OperationsPage:
        rows = _rows(executions, funding).subquery()
        statement = (
            select(rows)
            .where(*_filters(rows, query))
            .order_by(rows.c.occurred_at.desc(), rows.c.source.desc(), rows.c.row_id.desc())
            .limit(query.limit + 1)
        )
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            found = connection.execute(statement).mappings().all()
        return OperationsPage.of([_operation_of(row) for row in found], query.limit)


def _rows(executions: ColumnElement[bool], funding: ColumnElement[bool]) -> CompoundSelect:
    of_executions = select(
        account_fills.c.executed_at.label("occurred_at"),
        literal(int(OperationSource.EXECUTION)).label("source"),
        account_fills.c.id.label("row_id"),
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
        account_funding.c.asset,
        literal(FUNDING, Text),
        null().cast(Numeric),
        null().cast(Numeric),
        literal(ZERO, Numeric),
        literal(ZERO, Numeric),
        account_funding.c.amount,
    ).where(funding)
    return union_all(of_executions, of_funding)


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
    )
