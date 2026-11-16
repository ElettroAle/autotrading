from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from decimal import Decimal
from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import ColumnElement, Connection, Engine, RowMapping, func, select, update
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.tables import flow_protections
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.tenancy.tenant_id import TenantId


class _ProtectionRow(TypedDict):
    client_order_id: UUID
    account_id: UUID
    flow_id: UUID
    asset: str
    kind: str
    trigger_price: Decimal
    exchange_order_id: str


class SqlAlchemyProtectionRepositoryAdapter:
    """The protections the platform placed on the positions of the flows of one tenant, under row level security
    (R3.1.2, ADR ordini-di-protezione-sull-exchange).

    A removed protection is only marked: its execution, read later from the exchange, still belongs to its flow.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def add(self, protection: PlacedProtection) -> None:
        statement = flow_protections.insert().values(tenant_id=self._tenant_id.value, **row_of(protection))
        try:
            with self._transaction() as connection:
                connection.execute(statement)
        except IntegrityError as error:
            # The keys of the account and of the flow admit only those of the tenant of the adapter.
            raise CrossTenantAccessError from error

    def placed(self, account_id: UUID, asset: str) -> tuple[PlacedProtection, ...]:
        query = (
            select(flow_protections)
            .where(*_in_force(account_id, asset))
            .order_by(flow_protections.c.placed_at, flow_protections.c.client_order_id)
        )
        with self._transaction() as connection:
            rows = connection.execute(query).mappings().all()
        return tuple(protection_of(row) for row in rows)

    def remove(self, account_id: UUID, asset: str) -> None:
        statement = update(flow_protections).where(*_in_force(account_id, asset)).values(removed_at=func.now())
        with self._transaction() as connection:
            connection.execute(statement)

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _in_force(account_id: UUID, asset: str) -> tuple[ColumnElement[bool], ...]:
    return (
        flow_protections.c.account_id == account_id,
        flow_protections.c.asset == asset,
        flow_protections.c.removed_at.is_(None),
    )


def row_of(protection: PlacedProtection) -> dict[str, object]:
    return {
        "client_order_id": protection.client_order_id.value,
        "account_id": protection.account_id,
        "flow_id": protection.flow_id,
        "asset": protection.asset,
        "kind": protection.kind.name.lower(),
        "trigger_price": protection.trigger_price,
        "exchange_order_id": protection.exchange_order_id,
    }


def protection_of(columns: RowMapping | Mapping[str, object]) -> PlacedProtection:
    row = cast("_ProtectionRow", columns)
    return PlacedProtection(
        account_id=row["account_id"],
        flow_id=row["flow_id"],
        asset=row["asset"],
        kind=ProtectionKind[row["kind"].upper()],
        trigger_price=row["trigger_price"],
        exchange_order_id=row["exchange_order_id"],
        client_order_id=ClientOrderId(row["client_order_id"]),
    )
