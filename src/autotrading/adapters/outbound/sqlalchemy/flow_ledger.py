from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Connection, Engine, RowMapping, func, select
from sqlalchemy.dialects.postgresql import insert

from autotrading.adapters.outbound.sqlalchemy.tables import (
    account_fill_cursors,
    account_fills,
    account_funding,
    account_movements,
    flow_position_totals,
    flow_totals,
)
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import (
    AccountLedger,
    BalanceMovement,
    Execution,
    ExecutionKind,
    FlowTotals,
    FundingEntry,
    FundingPayment,
    LedgerEntry,
    LedgerKeys,
)
from autotrading.domain.tenancy.tenant_id import TenantId

ZERO = Decimal(0)


class SqlAlchemyFlowLedgerAdapter:
    """The ledger of the executions and the movements of the accounts and the running totals of the flows, bound to
    the tenant of the request.

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
        movements = select(account_movements.c.movement_id, account_movements.c.moved_at).where(
            account_movements.c.account_id == account_id, account_movements.c.moved_at >= since
        )
        with self._transaction() as connection:
            executions = frozenset((str(fill_id), str(order)) for fill_id, order in connection.execute(fills))
            payments = frozenset((str(asset), paid_at) for asset, paid_at in connection.execute(funding))
            moved = frozenset((str(movement_id), moved_at) for movement_id, moved_at in connection.execute(movements))
        return LedgerKeys(executions, payments, moved)

    def recorded_after(self, account_id: UUID, since: datetime) -> AccountLedger:
        fills = (
            select(account_fills)
            .where(account_fills.c.account_id == account_id, account_fills.c.executed_at > since)
            .order_by(account_fills.c.executed_at, account_fills.c.id)
        )
        funding = (
            select(account_funding)
            .where(account_funding.c.account_id == account_id, account_funding.c.paid_at > since)
            .order_by(account_funding.c.paid_at, account_funding.c.id)
        )
        movements = (
            select(account_movements)
            .where(account_movements.c.account_id == account_id, account_movements.c.moved_at > since)
            .order_by(account_movements.c.moved_at, account_movements.c.id)
        )
        with self._transaction() as connection:
            entries = tuple(_entry_of(row) for row in connection.execute(fills).mappings())
            payments = tuple(_funding_of(row) for row in connection.execute(funding).mappings())
            moved = tuple(_movement_of(row) for row in connection.execute(movements).mappings())
        return AccountLedger(entries, payments, moved)

    def record(self, account_id: UUID, ledger: AccountLedger, cursor: datetime) -> AccountLedger:
        with self._transaction() as connection:
            added = tuple(entry for entry in ledger.entries if self._add_execution(connection, account_id, entry))
            paid = tuple(payment for payment in ledger.funding if self._add_funding(connection, account_id, payment))
            moved = tuple(
                movement for movement in ledger.movements if self._add_movement(connection, account_id, movement)
            )
            self._move_cursor(connection, account_id, cursor)
        return AccountLedger(added, paid, moved)

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

    def _add_funding(self, connection: Connection, account_id: UUID, entry: FundingEntry) -> bool:
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
        if connection.execute(statement).first() is None:
            return False
        if flow_id is not None:
            self._add_to_totals(connection, flow_id, ZERO, ZERO, payment.amount)
        return True

    def _add_movement(self, connection: Connection, account_id: UUID, movement: BalanceMovement) -> bool:
        statement = (
            insert(account_movements)
            .values(
                tenant_id=self._tenant_id.value,
                account_id=account_id,
                movement_id=movement.movement_id,
                amount=movement.amount,
                moved_at=movement.moved_at,
            )
            .on_conflict_do_nothing(constraint="account_movements_once")
            .returning(account_movements.c.id)
        )
        return connection.execute(statement).first() is not None

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


def _flow_of(row: RowMapping) -> FlowId | None:
    return None if row["flow_id"] is None else FlowId(row["flow_id"])


def _entry_of(row: RowMapping) -> LedgerEntry:
    execution = Execution(
        fill_id=row["fill_id"],
        exchange_order_id=row["exchange_order_id"],
        order_id=row["order_id"],
        asset=row["asset"],
        size=row["size"],
        price=row["price"],
        fee=row["fee"],
        realized_pnl=row["realized_pnl"],
        start_position=row["start_position"],
        liquidation=row["liquidation"],
        executed_at=row["executed_at"],
    )
    return LedgerEntry(execution, _flow_of(row), ExecutionKind(row["kind"]), platform_order=row["platform_order"])


def _funding_of(row: RowMapping) -> FundingEntry:
    return FundingEntry(FundingPayment(row["asset"], row["amount"], row["paid_at"]), _flow_of(row))


def _movement_of(row: RowMapping) -> BalanceMovement:
    return BalanceMovement(row["movement_id"], row["amount"], row["moved_at"])
