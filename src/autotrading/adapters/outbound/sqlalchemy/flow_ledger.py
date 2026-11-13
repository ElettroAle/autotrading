from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Connection, Engine, func, select
from sqlalchemy.dialects.postgresql import insert

from autotrading.adapters.outbound.sqlalchemy.tables import (
    account_fill_cursors,
    account_fills,
    account_funding,
    flow_position_totals,
    flow_totals,
)
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import AccountLedger, FlowTotals, FundingEntry, LedgerEntry, LedgerKeys
from autotrading.domain.tenancy.tenant_id import TenantId

ZERO = Decimal(0)


class SqlAlchemyFlowLedgerAdapter:
    """The ledger of the executions and the running totals of the flows, bound to the tenant of the request.

    A row enters the ledger once, by the unique key of the exchange; the totals change only for a row that was
    really added, in the same transaction, so two cycles of the same account never count an execution twice.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def cursor(self, account_id: UUID) -> datetime | None:
        query = select(account_fill_cursors.c.last_executed_at).where(account_fill_cursors.c.account_id == account_id)
        with self._transaction() as connection:
            cursor: datetime | None = connection.execute(query).scalar_one_or_none()
        return cursor

    def recorded_since(self, account_id: UUID, since: datetime) -> LedgerKeys:
        fills = select(account_fills.c.fill_id, account_fills.c.exchange_order_id).where(
            account_fills.c.account_id == account_id, account_fills.c.executed_at >= since
        )
        funding = select(account_funding.c.asset, account_funding.c.paid_at).where(
            account_funding.c.account_id == account_id, account_funding.c.paid_at >= since
        )
        with self._transaction() as connection:
            executions = frozenset((str(fill_id), str(order)) for fill_id, order in connection.execute(fills))
            payments = frozenset((str(asset), paid_at) for asset, paid_at in connection.execute(funding))
        return LedgerKeys(executions, payments)

    def record(self, account_id: UUID, ledger: AccountLedger, cursor: datetime) -> tuple[LedgerEntry, ...]:
        with self._transaction() as connection:
            added = tuple(entry for entry in ledger.entries if self._add_execution(connection, account_id, entry))
            for payment in ledger.funding:
                self._add_funding(connection, account_id, payment)
            self._move_cursor(connection, account_id, cursor)
        return added

    def totals_of(self, flow_ids: Iterable[FlowId]) -> Mapping[FlowId, FlowTotals]:
        identifiers = [flow_id.value for flow_id in flow_ids]
        totals = select(flow_totals).where(flow_totals.c.flow_id.in_(identifiers))
        positions = select(flow_position_totals).where(flow_position_totals.c.flow_id.in_(identifiers))
        with self._transaction() as connection:
            rows = connection.execute(totals).mappings().all()
            held: dict[UUID, dict[str, Decimal]] = defaultdict(dict)
            for row in connection.execute(positions).mappings():
                held[row["flow_id"]][row["asset"]] = row["size"]
        return {
            FlowId(row["flow_id"]): FlowTotals(
                FlowId(row["flow_id"]),
                row["realized_pnl"],
                row["fees"],
                row["funding"],
                frozendict(held[row["flow_id"]]),
            )
            for row in rows
        }

    def recomputed_totals(self, flow_id: FlowId) -> FlowTotals:
        """The totals summed again from the whole ledger: a check run on demand, never by the cycle."""
        executions = select(
            func.coalesce(func.sum(account_fills.c.realized_pnl), ZERO),
            func.coalesce(func.sum(account_fills.c.fee), ZERO),
        ).where(account_fills.c.flow_id == flow_id.value)
        funding = select(func.coalesce(func.sum(account_funding.c.amount), ZERO)).where(
            account_funding.c.flow_id == flow_id.value
        )
        positions = (
            select(account_fills.c.asset, func.sum(account_fills.c.size))
            .where(account_fills.c.flow_id == flow_id.value)
            .group_by(account_fills.c.asset)
        )
        with self._transaction() as connection:
            realized, fees = connection.execute(executions).one()
            paid = connection.execute(funding).scalar_one()
            held = {str(asset): size for asset, size in connection.execute(positions)}
        return FlowTotals(flow_id, realized, fees, paid, frozendict(held))

    def _add_execution(self, connection: Connection, account_id: UUID, entry: LedgerEntry) -> bool:
        execution = entry.execution
        flow_id = None if entry.flow_id is None else entry.flow_id.value
        statement = (
            insert(account_fills)
            .values(
                tenant_id=self._tenant_id.value,
                account_id=account_id,
                fill_id=execution.fill_id,
                exchange_order_id=execution.exchange_order_id,
                flow_id=flow_id,
                order_id=execution.order_id,
                kind=entry.kind.value,
                platform_order=entry.platform_order,
                asset=execution.asset,
                size=execution.size,
                price=execution.price,
                fee=execution.fee,
                realized_pnl=execution.realized_pnl,
                start_position=execution.start_position,
                liquidation=execution.liquidation,
                executed_at=execution.executed_at,
            )
            .on_conflict_do_nothing(constraint="account_fills_once")
            .returning(account_fills.c.id)
        )
        if connection.execute(statement).first() is None:
            return False
        if flow_id is not None:
            self._add_to_totals(connection, flow_id, execution.realized_pnl, execution.fee, ZERO)
            self._add_to_position(connection, flow_id, execution.asset, execution.size)
        return True

    def _add_funding(self, connection: Connection, account_id: UUID, entry: FundingEntry) -> None:
        payment = entry.payment
        flow_id = None if entry.flow_id is None else entry.flow_id.value
        statement = (
            insert(account_funding)
            .values(
                tenant_id=self._tenant_id.value,
                account_id=account_id,
                flow_id=flow_id,
                asset=payment.asset,
                amount=payment.amount,
                paid_at=payment.paid_at,
            )
            .on_conflict_do_nothing(constraint="account_funding_once")
            .returning(account_funding.c.id)
        )
        if connection.execute(statement).first() is not None and flow_id is not None:
            self._add_to_totals(connection, flow_id, ZERO, ZERO, payment.amount)

    def _add_to_totals(
        self, connection: Connection, flow_id: UUID, realized_pnl: Decimal, fee: Decimal, funding: Decimal
    ) -> None:
        statement = insert(flow_totals).values(
            flow_id=flow_id, tenant_id=self._tenant_id.value, realized_pnl=realized_pnl, fees=fee, funding=funding
        )
        statement = statement.on_conflict_do_update(
            index_elements=[flow_totals.c.flow_id],
            set_={
                "realized_pnl": flow_totals.c.realized_pnl + statement.excluded.realized_pnl,
                "fees": flow_totals.c.fees + statement.excluded.fees,
                "funding": flow_totals.c.funding + statement.excluded.funding,
            },
        )
        connection.execute(statement)

    def _add_to_position(self, connection: Connection, flow_id: UUID, asset: str, size: Decimal) -> None:
        statement = insert(flow_position_totals).values(
            flow_id=flow_id, asset=asset, tenant_id=self._tenant_id.value, size=size
        )
        statement = statement.on_conflict_do_update(
            index_elements=[flow_position_totals.c.flow_id, flow_position_totals.c.asset],
            set_={"size": flow_position_totals.c.size + statement.excluded.size},
        )
        connection.execute(statement)

    def _move_cursor(self, connection: Connection, account_id: UUID, cursor: datetime) -> None:
        statement = insert(account_fill_cursors).values(
            account_id=account_id, tenant_id=self._tenant_id.value, last_executed_at=cursor
        )
        # A late cycle never moves the cursor back.
        statement = statement.on_conflict_do_update(
            index_elements=[account_fill_cursors.c.account_id],
            set_={
                "last_executed_at": func.greatest(
                    account_fill_cursors.c.last_executed_at, statement.excluded.last_executed_at
                )
            },
        )
        connection.execute(statement)

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection
