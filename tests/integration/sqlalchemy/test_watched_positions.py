"""The positions the platform watches for the stop that follows the price, on PostgreSQL under row level security
(R5.5.1, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select, text

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.watched_positions import SqlAlchemyWatchedPositionsAdapter
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.watched_position import WatchedPosition
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration

OPENED = datetime(2026, 11, 26, 9, tzinfo=UTC)
WATCHED = WatchedPosition("BTC", OPENED, Decimal("63000.5"), Decimal("30.005"), "stop BTC non aggiornato, rifiutato")


def new_flow(database: Engine, tenant_id: TenantId | None = None) -> tuple[TenantId, FlowId]:
    if tenant_id is None:
        tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
        SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
        tenant_id = tenant.id
    account = an_account(tenant_id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant_id).add(account)
    flow = a_flow(tenant_id, name=f"flusso-{uuid4()}", account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant_id).add(flow)
    return tenant_id, flow.id


def test_a_saved_position_reads_back_whole_and_without_rounding(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    positions = SqlAlchemyWatchedPositionsAdapter(database, tenant_id)

    positions.save(flow_id, WATCHED)

    assert positions.watched_of(flow_id) == (WATCHED,)


def test_a_position_without_opening_and_refusal_reads_back_empty(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    positions = SqlAlchemyWatchedPositionsAdapter(database, tenant_id)
    bare = WatchedPosition("ETH", None, Decimal(3000), Decimal(0))

    positions.save(flow_id, bare)

    assert positions.watched_of(flow_id) == (bare,)


def test_a_new_save_replaces_the_position_on_its_asset(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    positions = SqlAlchemyWatchedPositionsAdapter(database, tenant_id)
    positions.save(flow_id, WATCHED)

    positions.save(flow_id, WATCHED.told())

    assert positions.watched_of(flow_id) == (WATCHED.told(),)


def test_a_forgotten_position_is_no_longer_watched(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    positions = SqlAlchemyWatchedPositionsAdapter(database, tenant_id)
    eth = WatchedPosition("ETH", OPENED, Decimal(3000), Decimal(0))
    positions.save(flow_id, WATCHED)
    positions.save(flow_id, eth)

    positions.forget(flow_id, "BTC")
    positions.forget(flow_id, "SOL")

    assert positions.watched_of(flow_id) == (eth,)


def test_only_the_flows_kept_keep_their_positions(database: Engine) -> None:
    tenant_id, kept = new_flow(database)
    _, dropped = new_flow(database, tenant_id)
    positions = SqlAlchemyWatchedPositionsAdapter(database, tenant_id)
    positions.save(kept, WATCHED)
    positions.save(dropped, WATCHED)

    positions.keep_only([kept])

    assert (positions.watched_of(kept), positions.watched_of(dropped)) == ((WATCHED,), ())
    positions.keep_only([])
    assert positions.watched_of(kept) == ()


def test_the_positions_of_a_tenant_are_invisible_to_another_tenant(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)
    SqlAlchemyWatchedPositionsAdapter(database, tenant_id).save(flow_id, WATCHED)
    others = SqlAlchemyWatchedPositionsAdapter(database, other_tenant)

    assert others.watched_of(flow_id) == ()
    others.forget(flow_id, "BTC")
    others.keep_only([])
    assert SqlAlchemyWatchedPositionsAdapter(database, tenant_id).watched_of(flow_id) == (WATCHED,)


def test_a_query_without_any_filter_sees_only_the_rows_of_its_tenant(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)
    SqlAlchemyWatchedPositionsAdapter(database, tenant_id).save(flow_id, WATCHED)

    for tenant in (other_tenant, None):
        with database.begin() as connection:
            if tenant is not None:
                connection.execute(select(func.set_config("app.tenant_id", str(tenant.value), True)))
            assert connection.execute(text("SELECT count(*) FROM flow_watched_positions")).scalar_one() == 0


def test_a_tenant_cannot_save_a_position_on_the_flow_of_another_tenant(database: Engine) -> None:
    _, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)

    with pytest.raises(CrossTenantAccessError):
        SqlAlchemyWatchedPositionsAdapter(database, other_tenant).save(flow_id, WATCHED)
