from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, RowMapping, func, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.order_repository import SqlAlchemyOrderRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import orders
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow
from tests.support.orders import CYCLE_PLANNED_AT, EXECUTED_AT, a_flow_order, a_rejected_order, an_executed_order

pytestmark = pytest.mark.integration


def new_account(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    return tenant.id, account.id.value


def rows_of(database: Engine, tenant_id: TenantId | None) -> list[RowMapping]:
    # A query written without any tenant filter: only row level security stands between tenants.
    with database.begin() as connection:
        if tenant_id is not None:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return list(connection.execute(select(orders)).mappings())


def test_an_executed_order_is_recorded_with_what_the_exchange_executed(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    order = an_executed_order(account_id)

    SqlAlchemyOrderRepositoryAdapter(database, tenant_id).add(order)

    (row,) = rows_of(database, tenant_id)
    assert (row["id"], row["status"], row["user_id"]) == (order.id.value, "FILLED", "oid-anna")
    assert (row["filled_size"], row["average_price"], row["fee"]) == (
        Decimal("0.0002"),
        Decimal("100030.5"),
        Decimal("0.009003"),
    )
    assert row["executed_at"] == EXECUTED_AT


def test_a_rejected_order_is_recorded_with_its_client_order_id(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    order = a_rejected_order(account_id)

    SqlAlchemyOrderRepositoryAdapter(database, tenant_id).add(order)

    (row,) = rows_of(database, tenant_id)
    assert (row["id"], row["status"], row["rejection_reason"]) == (order.id.value, "REJECTED", "INSUFFICIENT_MARGIN")


def test_an_order_of_a_flow_is_recorded_with_the_flow_the_cycle_and_the_decision(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow = a_flow(tenant_id, name=f"alfa-{uuid4()}", account_id=account_id)
    SqlAlchemyFlowRepositoryAdapter(database, tenant_id).add(flow)

    SqlAlchemyOrderRepositoryAdapter(database, tenant_id).add(a_flow_order(account_id, flow.id.value))

    (row,) = rows_of(database, tenant_id)
    assert (row["origin"], row["flow_id"], row["cycle_planned_at"], row["decision_asset"]) == (
        "FLOW",
        flow.id.value,
        CYCLE_PLANNED_AT,
        "BTC",
    )


def test_an_order_of_a_flow_of_another_tenant_cannot_be_written(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    other_tenant, other_account = new_account(database)
    flow = a_flow(other_tenant, name=f"alfa-{uuid4()}", account_id=other_account)
    SqlAlchemyFlowRepositoryAdapter(database, other_tenant).add(flow)

    with pytest.raises(IntegrityError):
        SqlAlchemyOrderRepositoryAdapter(database, tenant_id).add(a_flow_order(account_id, flow.id.value))


def test_the_orders_of_a_tenant_are_invisible_to_another_and_without_a_tenant(database: Engine) -> None:
    anna, account_id = new_account(database)
    bruno, _ = new_account(database)
    SqlAlchemyOrderRepositoryAdapter(database, anna).add(an_executed_order(account_id))

    assert (len(rows_of(database, bruno)), len(rows_of(database, None))) == (0, 0)


def test_an_order_on_an_account_of_another_tenant_cannot_be_written(database: Engine) -> None:
    anna, account_id = new_account(database)
    bruno, _ = new_account(database)

    with pytest.raises(IntegrityError, match="orders_account_of_tenant"):
        SqlAlchemyOrderRepositoryAdapter(database, bruno).add(an_executed_order(account_id))

    assert (rows_of(database, anna), rows_of(database, bruno)) == ([], [])


def test_a_row_for_another_tenant_cannot_be_written(database: Engine) -> None:
    anna, account_id = new_account(database)
    bruno, _ = new_account(database)
    statement = text(
        "INSERT INTO orders (id, tenant_id, account_id, origin, coin, direction, reduce_only, leverage, "
        "requested_size, slippage, status) "
        "VALUES (:id, :tenant, :account, 'VERIFICATION', 'BTC', 'long', false, 2, 0.001, 0.05, 'UNKNOWN')"
    )

    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(bruno.value), True)))
        with pytest.raises(ProgrammingError, match="row-level security"):
            connection.execute(statement, {"id": uuid4(), "tenant": anna.value, "account": account_id})


def test_the_application_cannot_change_a_recorded_order(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    SqlAlchemyOrderRepositoryAdapter(database, tenant_id).add(an_executed_order(account_id))

    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        with pytest.raises(ProgrammingError, match="permission denied"):
            connection.execute(text("UPDATE orders SET status = 'REJECTED'"))
