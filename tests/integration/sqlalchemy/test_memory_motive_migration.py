"""ADR memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni: the versions saved before the length of the
motive and the choice of the decisions, with the memory on or off, read with 160 characters and only openings, closings
and reversals, without a new version; the decisions recorded before read back without motive nor invalidation."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, insert, select

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter, document_of
from autotrading.adapters.outbound.sqlalchemy.tables import cycle_decisions, cycles, flow_versions
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.recorded_decision import DecidedCycle, DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow
from tests.support.postgres import database_migrated_to

pytestmark = pytest.mark.integration

BEFORE_THE_MOTIVE = "0058"
PLANNED = datetime(2026, 11, 24, 10, 0, tzinfo=UTC)


def new_flow(database: Engine) -> Flow:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, "conto", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return flow


def old_version(database: Engine, flow: Flow, version: int, *, active: bool) -> None:
    """A version as the platform saved it before the length and the choice: its memory without them."""
    document = document_of(a_configuration()) | {"memory": {"active": active, "decisions": 5, "days": 14}}
    tenant_id = flow.tenant_id.value
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id), True)))
        connection.execute(
            insert(flow_versions).values(
                flow_id=flow.id.value, version=version, tenant_id=tenant_id, configuration=document
            )
        )


def test_the_versions_saved_before_on_or_off_read_with_160_characters_and_no_update(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_MOTIVE) as (database, migrate_the_rest):
        flow = new_flow(database)
        old_version(database, flow, 2, active=False)
        old_version(database, flow, 3, active=True)

        migrate_the_rest()

        flows = SqlAlchemyFlowRepositoryAdapter(database, flow.tenant_id)
        assert flows.get(flow.id).configuration.memory == FlowMemory(active=True, decisions=5, days=14)
        tenant_id = str(flow.tenant_id.value)
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", tenant_id, True)))
            saved = connection.execute(select(flow_versions.c.version, flow_versions.c.configuration)).all()
        memories = {version: configuration["memory"] for version, configuration in saved}
        assert {version: (memory["text_length"], memory["all_decisions"]) for version, memory in memories.items()} == {
            1: (160, False),
            2: (160, False),
            3: (160, False),
        }
        assert memories[3]["active"] is True


def test_the_decisions_recorded_before_read_back_without_motive_nor_invalidation(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_MOTIVE) as (database, migrate_the_rest):
        flow = new_flow(database)
        tenant_id = flow.tenant_id.value
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id), True)))
            connection.execute(
                insert(cycles).values(
                    flow_id=flow.id.value, planned_at=PLANNED, tenant_id=tenant_id, outcome="completed"
                )
            )
            connection.execute(
                insert(cycle_decisions).values(
                    flow_id=flow.id.value,
                    planned_at=PLANNED,
                    position=0,
                    tenant_id=tenant_id,
                    asset="BTC",
                    action="apri",
                    direction="long",
                    confidence=70,
                    reasoning="rottura",
                )
            )

        migrate_the_rest()

        decided = SqlAlchemyCycleRepositoryAdapter(database, flow.tenant_id).last_decided(flow.id.value)
        opening = RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 70, "rottura")
        assert decided == DecidedCycle(PLANNED, (opening,))
