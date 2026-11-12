from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, RowMapping, func, select
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.order_repository import SqlAlchemyOrderRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.platform_orders import SqlAlchemyPlatformOrdersAdapter
from autotrading.adapters.outbound.sqlalchemy.reconciliation_repository import (
    SqlAlchemyReconciliationRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.tables import unattributable_items
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import PlatformOrder
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.orders.order import Order
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow
from tests.support.orders import EXECUTION, a_flow_order, a_request, an_executed_order

pytestmark = pytest.mark.integration

READ_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def new_account(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    return tenant.id, account.id.value


def a_position(account_id: UUID, asset: str = "SOL") -> UnattributableItem:
    return UnattributableItem(account_id, UnattributableKind.POSITION, asset, asset, Decimal("1.5"), READ_AT)


def rows_of(database: Engine, tenant_id: TenantId | None) -> list[RowMapping]:
    # A query written without any tenant filter: only row level security stands between tenants.
    with database.begin() as connection:
        if tenant_id is not None:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return list(connection.execute(select(unattributable_items)).mappings())


def test_without_a_reading_the_account_has_none(database: Engine) -> None:
    tenant_id, account_id = new_account(database)

    assert SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id).last_reading(account_id) is None


def test_the_last_reading_replaces_the_previous_one(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)
    flow_id = FlowId.new()
    repository.save_reading(AccountReading(account_id, READ_AT.replace(hour=9), {flow_id: frozenset({"ETH"})}))

    repository.save_reading(AccountReading(account_id, READ_AT, {flow_id: frozenset({"BTC", "SOL"})}))

    assert repository.last_reading(account_id) == AccountReading(
        account_id, READ_AT, {flow_id: frozenset({"BTC", "SOL"})}
    )


def test_a_case_is_recorded_once_with_the_values_read(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)

    assert repository.record(a_position(account_id)) is True
    assert repository.record(a_position(account_id)) is False

    (row,) = rows_of(database, tenant_id)
    assert (row["kind"], row["reference"], row["asset"], row["amount"]) == ("position", "SOL", "SOL", Decimal("1.5"))
    assert (row["detected_at"], row["resolved_at"]) == (READ_AT, None)


def test_a_movement_without_an_asset_is_recorded(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    movement = UnattributableItem(account_id, UnattributableKind.BALANCE_CHANGE, "0xfeed", None, Decimal(200), READ_AT)

    assert SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id).record(movement) is True

    (row,) = rows_of(database, tenant_id)
    assert (row["kind"], row["asset"], row["amount"]) == ("balance_change", None, Decimal(200))


def test_a_position_no_longer_open_is_resolved_and_can_be_recorded_again(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyReconciliationRepositoryAdapter(database, tenant_id)
    repository.record(a_position(account_id, "SOL"))
    repository.record(a_position(account_id, "DOGE"))

    repository.resolve_positions(account_id, frozenset({"DOGE"}))

    assert repository.record(a_position(account_id, "SOL")) is True
    assert repository.record(a_position(account_id, "DOGE")) is False
    resolved = [row["reference"] for row in rows_of(database, tenant_id) if row["resolved_at"] is not None]
    assert resolved == ["SOL"]


def test_the_cases_of_a_tenant_are_invisible_to_another_and_without_a_tenant(database: Engine) -> None:
    anna, account_id = new_account(database)
    bruno, _ = new_account(database)
    SqlAlchemyReconciliationRepositoryAdapter(database, anna).record(a_position(account_id))

    assert (len(rows_of(database, bruno)), len(rows_of(database, None))) == (0, 0)
    assert SqlAlchemyReconciliationRepositoryAdapter(database, bruno).last_reading(account_id) is None


def test_a_case_on_an_account_of_another_tenant_cannot_be_written(database: Engine) -> None:
    _, account_id = new_account(database)
    bruno, _ = new_account(database)

    with pytest.raises(IntegrityError, match="unattributable_items_account_of_tenant"):
        SqlAlchemyReconciliationRepositoryAdapter(database, bruno).record(a_position(account_id))


def test_the_orders_of_the_platform_are_those_of_the_account_with_their_flow_and_origin(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    _, other_account = new_account(database)
    flow = a_flow(tenant_id, name=f"alfa-{uuid4()}", account_id=account_id)
    SqlAlchemyFlowRepositoryAdapter(database, tenant_id).add(flow)
    manual, of_flow = an_executed_order(account_id), a_flow_order(account_id, flow.id.value)
    SqlAlchemyOrderRepositoryAdapter(database, tenant_id).add(manual)
    SqlAlchemyOrderRepositoryAdapter(database, tenant_id).add(of_flow)
    verification = Order.executed(a_request(account_id), EXECUTION)
    SqlAlchemyOrderRepositoryAdapter(database, tenant_id).add(verification)

    orders = SqlAlchemyPlatformOrdersAdapter(database, tenant_id)

    asked = (manual.id.value, of_flow.id.value, verification.id.value, uuid4())
    assert orders.orders_among(account_id, asked) == {
        manual.id.value: PlatformOrder(None),
        of_flow.id.value: PlatformOrder(flow.id),
        verification.id.value: PlatformOrder(None, verification=True),
    }
    assert orders.orders_among(other_account, asked) == {}
    assert orders.orders_among(account_id, ()) == {}
