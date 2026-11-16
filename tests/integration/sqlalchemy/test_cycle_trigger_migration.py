"""ADR ciclo-su-richiesta-nel-worker: the cycles recorded before the trigger existed read as planned after the
migration; a cycle asked for now reads back as asked; a trigger the platform does not know is refused.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_trigger import CycleTrigger
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow
from tests.support.postgres import database_migrated_to

pytestmark = pytest.mark.integration

BEFORE_THE_TRIGGER = "0031"
PLANNED = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)
ASKED = datetime(2026, 11, 12, 10, 20, tzinfo=UTC)
# A cycle as the platform recorded it before the trigger, without its column.
INSERT_WITHOUT_TRIGGER = (
    "INSERT INTO cycles (flow_id, planned_at, tenant_id, outcome) VALUES (:flow, :planned, :tenant, 'skipped')"
)
INSERT_WITH_TRIGGER = (
    "INSERT INTO cycles (flow_id, planned_at, tenant_id, outcome, trigger) "
    "VALUES (:flow, :planned, :tenant, 'skipped', :trigger)"
)


def new_flow(database: Engine) -> tuple[Tenant, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, "conto", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return tenant, flow.id.value


def insert_cycle(database: Engine, tenant: Tenant, statement: str, values: dict[str, object]) -> None:
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant.id.value), True)))
        connection.execute(text(statement), {"planned": PLANNED, "tenant": tenant.id.value, **values})


def test_a_cycle_recorded_before_the_trigger_reads_as_planned(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_TRIGGER) as (database, migrate_the_rest):
        tenant, flow_id = new_flow(database)
        insert_cycle(database, tenant, INSERT_WITHOUT_TRIGGER, {"flow": flow_id})

        migrate_the_rest()

        cycles = SqlAlchemyCycleRepositoryAdapter(database, tenant.id)
        assert cycles.at(flow_id, PLANNED) == CycleRecord.skipped(flow_id, PLANNED)


def test_a_cycle_asked_for_now_reads_back_as_asked(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_TRIGGER) as (database, migrate_the_rest):
        migrate_the_rest()
        tenant, flow_id = new_flow(database)
        cycles = SqlAlchemyCycleRepositoryAdapter(database, tenant.id)
        asked = CycleRecord(flow_id, ASKED, CycleOutcome.COMPLETED, trigger=CycleTrigger.ON_DEMAND)

        cycles.claim(flow_id, ASKED)
        cycles.record(asked)

        assert cycles.at(flow_id, ASKED) == asked


def test_a_trigger_the_platform_does_not_know_is_refused(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_TRIGGER) as (database, migrate_the_rest):
        migrate_the_rest()
        tenant, flow_id = new_flow(database)

        with pytest.raises(IntegrityError):
            insert_cycle(database, tenant, INSERT_WITH_TRIGGER, {"flow": flow_id, "trigger": "manual"})
