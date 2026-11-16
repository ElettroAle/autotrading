"""ADR decisioni-del-ciclo-registrate-per-asset: the decisions of the cycles recorded before the table existed are
copied from the document of the decision step, in their order, with the confidence when the agent gave one.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, func, insert, select

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import cycles
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.recorded_decision import DecidedCycle, DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow
from tests.support.postgres import database_migrated_to

pytestmark = pytest.mark.integration

BEFORE_THE_DECISIONS = "0031"
DECIDED_AT = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)
FAILED_AT = datetime(2026, 11, 16, 11, 0, tzinfo=UTC)
# The decisions as the journal of the cycle wrote them: an opening with its fields, a hold given before the agent had
# a confidence.
DOCUMENTS = [
    {"step": "compose_context", "content": {"messaggi": []}},
    {
        "step": "agent_decision",
        "content": {
            "risposta": "{}",
            "decisioni": [
                {
                    "tipo": "Decision",
                    "asset": "BTC",
                    "action": "apri",
                    "reasoning": "trend rialzista",
                    "confidence": 72,
                    "opening": {"tipo": "TradeOpening", "direction": "long", "margin_fraction": "0.1", "leverage": 3},
                    "plan_change": None,
                },
                {"tipo": "Decision", "asset": "ETH", "action": "mantieni", "reasoning": "attesa", "opening": None},
            ],
            "scartate": [],
            "mancanti": [],
        },
    },
]


def new_flow(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, "conto", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return tenant.id, flow.id.value


def record_as_before(database: Engine, tenant_id: TenantId, flow_id: UUID) -> None:
    common = {"flow_id": flow_id, "tenant_id": tenant_id.value, "steps": [], "absent_sources": []}
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        connection.execute(
            insert(cycles).values(
                [
                    common | {"planned_at": DECIDED_AT, "outcome": "completed", "documents": DOCUMENTS},
                    common | {"planned_at": FAILED_AT, "outcome": "failed", "documents": DOCUMENTS[:1]},
                ]
            )
        )


def test_the_decisions_of_the_cycles_recorded_before_are_copied_from_their_documents(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_DECISIONS) as (database, migrate_the_rest):
        tenant_id, flow_id = new_flow(database)
        record_as_before(database, tenant_id, flow_id)

        migrate_the_rest()

        assert SqlAlchemyCycleRepositoryAdapter(database, tenant_id).last_decided(flow_id) == DecidedCycle(
            DECIDED_AT,
            (
                RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 72, "trend rialzista"),
                RecordedDecision("ETH", DecisionAction.HOLD, None, None, "attesa"),
            ),
        )


def test_a_tenant_reads_only_the_decisions_copied_from_its_cycles(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_DECISIONS) as (database, migrate_the_rest):
        tenant_id, flow_id = new_flow(database)
        other_tenant, _ = new_flow(database)
        record_as_before(database, tenant_id, flow_id)

        migrate_the_rest()

        assert SqlAlchemyCycleRepositoryAdapter(database, other_tenant).last_decided(flow_id) is None
