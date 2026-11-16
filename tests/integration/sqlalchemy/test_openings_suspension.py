"""The openings suspended for maximum loss, saved beside the flow under row level security (R3.2.2)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.openings_suspension import SqlAlchemyOpeningsSuspensionAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.openings_suspension import NOT_SUSPENDED, OpeningsStatus, OpeningsSuspension
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration

SUSPENDED_AT = datetime(2026, 11, 16, 10, tzinfo=UTC)
SUSPENSION = OpeningsSuspension("perdita giornaliera 6% oltre il 5%", SUSPENDED_AT)


def new_flow(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, name=f"flusso-{uuid4()}", account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return tenant.id, flow.id.value


def test_a_new_flow_has_its_openings_never_suspended(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)

    assert SqlAlchemyOpeningsSuspensionAdapter(database, tenant_id).status(flow_id) == NOT_SUSPENDED


def test_a_suspension_reads_back_and_a_resume_lifts_it_keeping_its_instant(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    openings = SqlAlchemyOpeningsSuspensionAdapter(database, tenant_id)

    openings.suspend(flow_id, SUSPENSION)
    suspended = openings.status(flow_id)
    openings.resume(flow_id, SUSPENDED_AT + timedelta(hours=2))

    assert suspended == OpeningsStatus(SUSPENSION, None)
    assert openings.status(flow_id) == OpeningsStatus(None, SUSPENDED_AT + timedelta(hours=2))


def test_a_new_suspension_keeps_the_last_resume(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    openings = SqlAlchemyOpeningsSuspensionAdapter(database, tenant_id)
    openings.resume(flow_id, SUSPENDED_AT - timedelta(days=1))

    openings.suspend(flow_id, SUSPENSION)

    assert openings.status(flow_id) == OpeningsStatus(SUSPENSION, SUSPENDED_AT - timedelta(days=1))


def test_the_openings_of_a_flow_of_another_tenant_are_neither_read_nor_written(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)
    stranger = SqlAlchemyOpeningsSuspensionAdapter(database, other_tenant)

    stranger.suspend(flow_id, SUSPENSION)
    SqlAlchemyOpeningsSuspensionAdapter(database, tenant_id).suspend(flow_id, SUSPENSION)
    stranger.resume(flow_id, SUSPENDED_AT)

    assert stranger.status(flow_id) == NOT_SUSPENDED
    assert SqlAlchemyOpeningsSuspensionAdapter(database, tenant_id).status(flow_id) == OpeningsStatus(SUSPENSION, None)
