"""The protections the platform placed for the flows, in PostgreSQL under row level security (R3.1.2)."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_protection_levels import SqlAlchemyFlowProtectionLevelsAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.platform_orders import SqlAlchemyPlatformOrdersAdapter
from autotrading.adapters.outbound.sqlalchemy.protection_repository import SqlAlchemyProtectionRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.exit_plan import PlacedLevels
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import PlatformOrder
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration


def new_flow(database: Engine) -> tuple[TenantId, UUID, FlowId]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, name=f"flusso-{uuid4()}", account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return tenant.id, account.id.value, flow.id


def a_protection(account_id: UUID, flow_id: FlowId, kind: ProtectionKind, asset: str = "BTC") -> PlacedProtection:
    return PlacedProtection(account_id, flow_id.value, asset, kind, Decimal("57000.5"), "4242", ClientOrderId.new())


def test_the_protections_of_a_position_read_back_until_they_are_removed(database: Engine) -> None:
    tenant_id, account_id, flow_id = new_flow(database)
    protections = SqlAlchemyProtectionRepositoryAdapter(database, tenant_id)
    stop = a_protection(account_id, flow_id, ProtectionKind.STOP_LOSS)
    take_profit = a_protection(account_id, flow_id, ProtectionKind.TAKE_PROFIT)
    other = a_protection(account_id, flow_id, ProtectionKind.STOP_LOSS, "ETH")
    for protection in (stop, take_profit, other):
        protections.add(protection)

    assert protections.placed(account_id, "BTC") == (stop, take_profit)
    protections.remove(account_id, "BTC")
    assert (protections.placed(account_id, "BTC"), protections.placed(account_id, "ETH")) == ((), (other,))


def test_a_removed_protection_is_still_an_order_of_its_flow_that_closes_the_position(database: Engine) -> None:
    tenant_id, account_id, flow_id = new_flow(database)
    protections = SqlAlchemyProtectionRepositoryAdapter(database, tenant_id)
    stop = a_protection(account_id, flow_id, ProtectionKind.STOP_LOSS)
    protections.add(stop)
    protections.remove(account_id, "BTC")

    found = SqlAlchemyPlatformOrdersAdapter(database, tenant_id).orders_among(account_id, [stop.client_order_id.value])

    assert found == {stop.client_order_id.value: PlatformOrder(flow_id, protection=CloseReason.STOP_LOSS)}


def test_the_protections_of_a_tenant_are_invisible_to_another_tenant(database: Engine) -> None:
    tenant_id, account_id, flow_id = new_flow(database)
    other_tenant, _, _ = new_flow(database)
    SqlAlchemyProtectionRepositoryAdapter(database, tenant_id).add(
        a_protection(account_id, flow_id, ProtectionKind.STOP_LOSS)
    )

    assert SqlAlchemyProtectionRepositoryAdapter(database, other_tenant).placed(account_id, "BTC") == ()


def test_a_protection_of_a_flow_of_another_tenant_is_refused(database: Engine) -> None:
    _, account_id, flow_id = new_flow(database)
    other_tenant, _, _ = new_flow(database)

    with pytest.raises(CrossTenantAccessError):
        SqlAlchemyProtectionRepositoryAdapter(database, other_tenant).add(
            a_protection(account_id, flow_id, ProtectionKind.STOP_LOSS)
        )


def test_a_replaced_protection_alone_is_removed_and_the_other_stays(database: Engine) -> None:
    tenant_id, account_id, flow_id = new_flow(database)
    protections = SqlAlchemyProtectionRepositoryAdapter(database, tenant_id)
    stop = a_protection(account_id, flow_id, ProtectionKind.STOP_LOSS)
    take_profit = a_protection(account_id, flow_id, ProtectionKind.TAKE_PROFIT)
    for protection in (stop, take_profit):
        protections.add(protection)

    protections.remove(account_id, "BTC", ProtectionKind.STOP_LOSS)

    assert protections.placed(account_id, "BTC") == (take_profit,)


def test_the_levels_in_force_of_a_flow_are_those_of_its_protections_not_removed(database: Engine) -> None:
    tenant_id, account_id, flow_id = new_flow(database)
    protections = SqlAlchemyProtectionRepositoryAdapter(database, tenant_id)
    levels = SqlAlchemyFlowProtectionLevelsAdapter(database, tenant_id)
    replaced = a_protection(account_id, flow_id, ProtectionKind.TAKE_PROFIT)
    protections.add(a_protection(account_id, flow_id, ProtectionKind.STOP_LOSS))
    protections.add(replaced)
    protections.remove(account_id, "BTC", ProtectionKind.TAKE_PROFIT)

    assert levels.placed_levels(flow_id, "BTC") == PlacedLevels(Decimal("57000.5"), None)
    assert levels.placed_levels(flow_id, "ETH") == PlacedLevels(None, None)


def test_the_levels_of_a_tenant_are_invisible_to_another_tenant(database: Engine) -> None:
    tenant_id, account_id, flow_id = new_flow(database)
    other_tenant, _, _ = new_flow(database)
    SqlAlchemyProtectionRepositoryAdapter(database, tenant_id).add(
        a_protection(account_id, flow_id, ProtectionKind.STOP_LOSS)
    )

    assert SqlAlchemyFlowProtectionLevelsAdapter(database, other_tenant).placed_levels(flow_id, "BTC") == (
        PlacedLevels(None, None)
    )
