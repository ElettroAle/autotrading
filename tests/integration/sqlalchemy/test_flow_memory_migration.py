"""ADR memoria-del-flusso-dalle-decisioni-operative-precedenti: the versions saved before the memory existed read with
the memory off, 10 decisions and 30 days, without a new version; the cycles keep the memory the agent received."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, insert, select

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter, document_of
from autotrading.adapters.outbound.sqlalchemy.tables import flow_versions
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.memory_entry import AssetMemory, MemoryEntry, MemoryOutcome
from autotrading.domain.flows.recorded_decision import DecisionAction
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow
from tests.support.postgres import database_migrated_to

pytestmark = pytest.mark.integration

BEFORE_THE_MEMORY = "0057"
MEMORY = "memory"
PLANNED = datetime(2026, 11, 24, 10, 0, tzinfo=UTC)


def new_flow(database: Engine, memory: FlowMemory | None = None) -> Flow:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, "conto", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    configuration = a_configuration() if memory is None else replace(a_configuration(), memory=memory)
    flow = a_flow(tenant.id, account_id=account.id.value, configuration=configuration)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return flow


def test_a_version_saved_before_the_memory_reads_with_it_off_and_its_defaults(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_MEMORY) as (database, migrate_the_rest):
        flow = new_flow(database)
        # The second version as the platform saved it before the memory: without its key.
        old_document = {key: value for key, value in document_of(a_configuration()).items() if key != MEMORY}
        tenant_id = flow.tenant_id.value
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id), True)))
            connection.execute(
                insert(flow_versions).values(
                    flow_id=flow.id.value, version=2, tenant_id=tenant_id, configuration=old_document
                )
            )

        migrate_the_rest()

        flows = SqlAlchemyFlowRepositoryAdapter(database, flow.tenant_id)
        assert flows.get(flow.id).configuration.memory == FlowMemory(active=False, decisions=10, days=30)
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id), True)))
            saved = connection.execute(select(flow_versions.c.configuration).where(flow_versions.c.version == 2))
            memory_document = saved.scalar_one()[MEMORY]
        assert memory_document == {
            "active": False,
            "decisions": 10,
            "days": 30,
            "text_length": 160,
            "all_decisions": False,
        }
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id), True)))
            versions = connection.execute(select(func.count()).select_from(flow_versions)).scalar_one()
        assert versions == 2


def test_the_memory_saved_after_the_migration_and_the_one_a_cycle_received_read_back(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_MEMORY) as (database, migrate_the_rest):
        migrate_the_rest()
        flow = new_flow(database, FlowMemory(active=True, decisions=5, days=14))
        entry = MemoryEntry(
            PLANNED,
            "BTC",
            DecisionAction.OPEN,
            TradeSide.LONG,
            Decimal("95000.5"),
            "rottura",
            "sotto 94000",
            MemoryOutcome(Decimal(3), realized=True, course="chiusa dallo stop loss dopo 12 minuti"),
        )
        memory = (AssetMemory("BTC", (entry,)),)
        cycles = SqlAlchemyCycleRepositoryAdapter(database, flow.tenant_id)
        cycles.record(CycleRecord(flow.id.value, PLANNED, CycleOutcome.COMPLETED, memory=memory))

        flows = SqlAlchemyFlowRepositoryAdapter(database, flow.tenant_id)
        assert flows.get(flow.id).configuration.memory == FlowMemory(active=True, decisions=5, days=14)
        recorded = cycles.at(flow.id.value, PLANNED)
        assert recorded is not None
        assert recorded.memory == memory
