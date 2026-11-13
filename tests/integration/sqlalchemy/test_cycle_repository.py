from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import cycles
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_record import (
    AbsentSource,
    CycleFailure,
    CycleOutcome,
    CycleRecord,
    StepDocument,
)
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_cost import CycleCost
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration

PLANNED = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)


def new_flow(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return tenant.id, flow.id.value


def a_failed_cycle(flow_id: UUID, planned_at: datetime = PLANNED) -> CycleRecord:
    return CycleRecord(
        flow_id=flow_id,
        planned_at=planned_at,
        outcome=CycleOutcome.FAILED,
        started_at=planned_at + timedelta(seconds=75),
        delay_seconds=75,
        steps=(CycleStep.READ_FLOW_STATE, CycleStep.COLLECT_SOURCES, CycleStep.COMPOSE_CONTEXT),
        absent_sources=(AbsentSource("notizie", "nessuna risposta entro 60 secondi"),),
        failure=CycleFailure(CycleStep.AGENT_DECISION, "ModelUnavailableError", "fornitore IA non raggiungibile"),
        documents=(StepDocument(CycleStep.COMPOSE_CONTEXT, {"messaggi": ["regole"], "margine": "50.10"}),),
        cost=CallCost(2000, 500, Decimal("0.0031")),
    )


def test_a_planned_instant_is_taken_only_once(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    first, second = (SqlAlchemyCycleRepositoryAdapter(database, tenant_id) for _ in range(2))

    assert first.claim(flow_id, PLANNED)
    assert not second.claim(flow_id, PLANNED)
    assert second.claim(flow_id, PLANNED + timedelta(minutes=15))


def test_a_taken_cycle_is_not_shown_until_it_is_recorded(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    repository.claim(flow_id, PLANNED)

    assert repository.newest(flow_id, 0, 50) == []
    assert repository.at(flow_id, PLANNED) is None


def test_a_recorded_cycle_reads_back_with_everything_it_produced(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    record = a_failed_cycle(flow_id)
    repository.claim(flow_id, PLANNED)

    repository.record(record)

    assert repository.at(flow_id, PLANNED) == record


def test_a_skipped_cycle_is_recorded_on_the_instant_it_took(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    repository.claim(flow_id, PLANNED)

    repository.record(CycleRecord.skipped(flow_id, PLANNED))

    assert repository.newest(flow_id, 0, 50) == [CycleRecord.skipped(flow_id, PLANNED)]


def test_the_cycles_come_from_the_most_recent_in_pages(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    for minutes in range(5):
        repository.record(CycleRecord.skipped(flow_id, PLANNED + timedelta(minutes=15 * minutes)))

    page = repository.newest(flow_id, 1, 2)

    assert [record.planned_at for record in page] == [PLANNED + timedelta(minutes=45), PLANNED + timedelta(minutes=30)]


def test_the_costs_are_those_of_the_cycles_that_called_the_model(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    repository = SqlAlchemyCycleRepositoryAdapter(database, tenant_id)
    repository.record(a_failed_cycle(flow_id))
    repository.record(CycleRecord.skipped(flow_id, PLANNED + timedelta(minutes=15)))
    unpriced = CycleRecord(flow_id, PLANNED + timedelta(minutes=30), CycleOutcome.COMPLETED, cost=CallCost(1, 1, None))
    repository.record(unpriced)

    assert repository.costs(flow_id) == [
        CycleCost(PLANNED, CallCost(2000, 500, Decimal("0.0031"))),
        CycleCost(PLANNED + timedelta(minutes=30), CallCost(1, 1, None)),
    ]


def test_the_cycles_of_another_tenant_stay_invisible(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)
    SqlAlchemyCycleRepositoryAdapter(database, tenant_id).record(a_failed_cycle(flow_id))
    other = SqlAlchemyCycleRepositoryAdapter(database, other_tenant)

    assert other.newest(flow_id, 0, 50) == []
    assert other.at(flow_id, PLANNED) is None
    assert other.costs(flow_id) == []


def test_a_tenant_cannot_record_a_cycle_of_a_flow_of_another_tenant(database: Engine) -> None:
    _, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)

    with pytest.raises(IntegrityError, match="violates foreign key"):
        SqlAlchemyCycleRepositoryAdapter(database, other_tenant).record(a_failed_cycle(flow_id))


def test_a_recorded_cycle_cannot_be_deleted(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    SqlAlchemyCycleRepositoryAdapter(database, tenant_id).record(a_failed_cycle(flow_id))

    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        with pytest.raises(ProgrammingError, match="permission denied"):
            connection.execute(cycles.delete())


def test_a_session_without_tenant_sees_no_cycle(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    SqlAlchemyCycleRepositoryAdapter(database, tenant_id).record(a_failed_cycle(flow_id))

    with database.begin() as connection:
        assert connection.execute(text("SELECT count(*) FROM cycles")).scalar_one() == 0
