from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, RowMapping, func, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.sample_repository import SqlAlchemySampleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import source_samples
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.sources.source_sample import CycleReference, SourceSample
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration

PLANNED = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)
REFERENCE = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
COLLECTED = datetime(2026, 11, 12, 10, 7, 2, tzinfo=UTC)


def new_flow(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, name=f"flusso-{uuid4()}", account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return tenant.id, flow.id.value


def samples_of(flow_id: UUID) -> list[SourceSample]:
    cycle = CycleReference(flow_id, PLANNED)
    return [
        SourceSample(cycle, "indicatori", "BTC", REFERENCE, COLLECTED, {"prezzo": "100.5"}),
        SourceSample(cycle, "notizie", None, REFERENCE, COLLECTED, {"titolo": "Bitcoin è salito"}),
    ]


def rows_of(database: Engine, tenant_id: TenantId | None) -> list[RowMapping]:
    # A query written without any tenant filter: only row level security stands between tenants.
    with database.begin() as connection:
        if tenant_id is not None:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return list(connection.execute(select(source_samples).order_by(source_samples.c.id)).mappings())


def test_every_sample_is_recorded_with_its_instants_and_its_cycle(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)

    SqlAlchemySampleRepositoryAdapter(database, tenant_id).add(samples_of(flow_id))

    recorded = [
        (
            row.flow_id,
            row.cycle_planned_at,
            row.source,
            row.asset,
            row.reference_at,
            row.collected_at,
            row.sample_values,
        )
        for row in rows_of(database, tenant_id)
    ]
    assert recorded == [
        (flow_id, PLANNED, "indicatori", "BTC", REFERENCE, COLLECTED, {"prezzo": "100.5"}),
        (flow_id, PLANNED, "notizie", None, REFERENCE, COLLECTED, {"titolo": "Bitcoin è salito"}),
    ]


def test_no_sample_writes_nothing(database: Engine) -> None:
    tenant_id, _ = new_flow(database)

    SqlAlchemySampleRepositoryAdapter(database, tenant_id).add([])

    assert rows_of(database, tenant_id) == []


def test_the_samples_of_a_tenant_are_invisible_to_another_tenant_and_without_tenant(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)

    SqlAlchemySampleRepositoryAdapter(database, tenant_id).add(samples_of(flow_id))

    assert rows_of(database, other_tenant) == []
    assert rows_of(database, None) == []


def test_a_tenant_cannot_record_samples_of_the_flow_of_another_tenant(database: Engine) -> None:
    _, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)

    with pytest.raises(IntegrityError):
        SqlAlchemySampleRepositoryAdapter(database, other_tenant).add(samples_of(flow_id))


def test_a_recorded_sample_is_never_changed_nor_deleted(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    SqlAlchemySampleRepositoryAdapter(database, tenant_id).add(samples_of(flow_id))

    for statement in ("UPDATE source_samples SET source = 'altro'", "DELETE FROM source_samples"):
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
            with pytest.raises(ProgrammingError, match="permission denied"):
                connection.execute(text(statement))
