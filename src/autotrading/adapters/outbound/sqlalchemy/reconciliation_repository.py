from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Connection, Engine, RowMapping, func, select, update
from sqlalchemy.dialects.postgresql import insert

from autotrading.adapters.outbound.sqlalchemy.tables import account_readings, unattributable_items
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.tenancy.tenant_id import TenantId

OPEN_CASE = unattributable_items.c.resolved_at.is_(None)


class SqlAlchemyReconciliationRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest.

    The unique index on the open cases makes "recorded once" hold also when two cycles of the account run together.
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
        values = {
            "account_id": reading.account_id,
            "tenant_id": self._tenant_id.value,
            "read_at": reading.read_at,
            "open_assets": {str(flow_id.value): sorted(assets) for flow_id, assets in reading.open_assets.items()},
        }
        statement = insert(account_readings).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=[account_readings.c.account_id],
            set_={"read_at": statement.excluded.read_at, "open_assets": statement.excluded.open_assets},
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

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _reading_of(row: RowMapping) -> AccountReading:
    open_assets = {FlowId(UUID(flow_id)): frozenset(assets) for flow_id, assets in row["open_assets"].items()}
    read_at: datetime = row["read_at"]
    return AccountReading(row["account_id"], read_at, open_assets)


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
