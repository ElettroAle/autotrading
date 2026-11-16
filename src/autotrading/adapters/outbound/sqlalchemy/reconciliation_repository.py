from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Connection, Engine, RowMapping, func, select, update
from sqlalchemy.dialects.postgresql import insert

from autotrading.adapters.outbound.sqlalchemy.tables import (
    account_readings,
    reconciliation_alarms,
    unattributable_items,
)
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.tenancy.tenant_id import TenantId

OPEN_CASE = unattributable_items.c.resolved_at.is_(None)
OPEN_ALARM = reconciliation_alarms.c.confirmed_at.is_(None)
READING_VALUES = ("read_at", "open_assets", "reference_balance", "expected_balance", "read_balance")


class SqlAlchemyReconciliationRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest.

    The unique indexes on the open cases and on the open alarms make "recorded once" and "one alarm open" hold also
    when two cycles of the account run together.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def last_reading(self, account_id: UUID) -> AccountReading | None:
        query = select(account_readings).where(account_readings.c.account_id == account_id)
        with self._transaction() as connection:
            row = connection.execute(query).mappings().one_or_none()
        return None if row is None else _reading_of(row)

    def save_reading(self, reading: AccountReading) -> None:
        statement = insert(account_readings).values(_reading_row_of(reading, self._tenant_id))
        statement = statement.on_conflict_do_update(
            index_elements=[account_readings.c.account_id],
            set_={column: statement.excluded[column] for column in READING_VALUES},
        )
        with self._transaction() as connection:
            connection.execute(statement)

    def record(self, item: UnattributableItem) -> bool:
        statement = (
            insert(unattributable_items)
            .values(_row_of(item, self._tenant_id))
            .on_conflict_do_nothing(
                index_elements=["tenant_id", "account_id", "kind", "reference"], index_where=OPEN_CASE
            )
            .returning(unattributable_items.c.id)
        )
        with self._transaction() as connection:
            return connection.execute(statement).first() is not None

    def resolve_positions(self, account_id: UUID, open_assets: frozenset[str]) -> None:
        statement = (
            update(unattributable_items)
            .where(
                OPEN_CASE,
                unattributable_items.c.account_id == account_id,
                unattributable_items.c.kind == UnattributableKind.POSITION.name.lower(),
                unattributable_items.c.reference.not_in(sorted(open_assets)),
            )
            .values(resolved_at=func.now())
        )
        with self._transaction() as connection:
            connection.execute(statement)

    def open_alarm(self, account_id: UUID) -> ReconciliationAlarm | None:
        query = select(reconciliation_alarms).where(OPEN_ALARM, reconciliation_alarms.c.account_id == account_id)
        with self._transaction() as connection:
            row = connection.execute(query).mappings().one_or_none()
        return None if row is None else _alarm_of(row)

    def open(self, alarm: ReconciliationAlarm) -> bool:
        statement = (
            insert(reconciliation_alarms)
            .values(_alarm_row_of(alarm, self._tenant_id))
            .on_conflict_do_nothing(index_elements=["tenant_id", "account_id"], index_where=OPEN_ALARM)
            .returning(reconciliation_alarms.c.id)
        )
        with self._transaction() as connection:
            return connection.execute(statement).first() is not None

    def confirm(self, account_id: UUID, at: datetime) -> bool:
        statement = (
            update(reconciliation_alarms)
            .where(OPEN_ALARM, reconciliation_alarms.c.account_id == account_id)
            .values(confirmed_at=at)
        )
        with self._transaction() as connection:
            return connection.execute(statement).rowcount == 1

    def alarms_of(self, account_id: UUID) -> list[ReconciliationAlarm]:
        query = (
            select(reconciliation_alarms)
            .where(reconciliation_alarms.c.account_id == account_id)
            .order_by(reconciliation_alarms.c.opened_at.desc(), reconciliation_alarms.c.id)
        )
        with self._transaction() as connection:
            return [_alarm_of(row) for row in connection.execute(query).mappings()]

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _reading_of(row: RowMapping) -> AccountReading:
    open_assets = {FlowId(UUID(flow_id)): frozenset(assets) for flow_id, assets in row["open_assets"].items()}
    read_at: datetime = row["read_at"]
    return AccountReading(
        row["account_id"], read_at, open_assets, row["reference_balance"], _comparison_of(row, read_at)
    )


def _comparison_of(row: RowMapping, read_at: datetime) -> BalanceComparison | None:
    expected: Decimal | None = row["expected_balance"]
    read: Decimal | None = row["read_balance"]
    if expected is None or read is None:
        return None
    return BalanceComparison(expected, read, read_at)


def _reading_row_of(reading: AccountReading, tenant_id: TenantId) -> dict[str, object]:
    comparison = reading.comparison
    return {
        "account_id": reading.account_id,
        "tenant_id": tenant_id.value,
        "read_at": reading.read_at,
        "open_assets": {str(flow_id.value): sorted(assets) for flow_id, assets in reading.open_assets.items()},
        "reference_balance": reading.reference_balance,
        "expected_balance": None if comparison is None else comparison.expected,
        "read_balance": None if comparison is None else comparison.read,
    }


def _alarm_of(row: RowMapping) -> ReconciliationAlarm:
    return ReconciliationAlarm(
        row["account_id"],
        row["expected_balance"],
        row["read_balance"],
        row["deviation_percent"],
        row["opened_at"],
        row["confirmed_at"],
    )


def _alarm_row_of(alarm: ReconciliationAlarm, tenant_id: TenantId) -> dict[str, object]:
    return {
        "id": uuid4(),
        "tenant_id": tenant_id.value,
        "account_id": alarm.account_id,
        "expected_balance": alarm.expected_balance,
        "read_balance": alarm.read_balance,
        "deviation_percent": alarm.deviation_percent,
        "opened_at": alarm.opened_at,
        "confirmed_at": alarm.confirmed_at,
    }


def _row_of(item: UnattributableItem, tenant_id: TenantId) -> dict[str, object]:
    return {
        "id": uuid4(),
        "tenant_id": tenant_id.value,
        "account_id": item.account_id,
        "kind": item.kind.name.lower(),
        "reference": item.reference,
        "asset": item.asset,
        "amount": item.amount,
        "detected_at": item.detected_at,
    }
