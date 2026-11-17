"""ADR costo-della-decisione-fallita-nel-registro-del-ciclo: the cycles recorded before the migration called the model
exactly when they kept its tokens, and keep counting among the costs of the flow.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import cycles
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.flow_cost import CycleCost
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow
from tests.support.postgres import database_migrated_to

pytestmark = pytest.mark.integration

BEFORE_THE_MODEL_CALL = "0033"
PLANNED = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)


def test_the_cycles_recorded_before_called_the_model_when_they_kept_its_tokens(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_MODEL_CALL) as (database, migrate_the_rest):
        tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
        SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
        account = an_account(tenant.id, "conto", SealedCredentials(1, b"\x00sealed"))
        SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
        flow = a_flow(tenant.id, account_id=account.id.value)
        SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
        # Two cycles as the platform recorded them before the migration: one with its call, one without.
        rows: list[dict[str, object]] = [
            {"planned_at": PLANNED, "input_tokens": 2000, "output_tokens": 500, "cost_usd": Decimal("0.0031")},
            {"planned_at": PLANNED + timedelta(minutes=15)},
        ]
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant.id.value), True)))
            for row in rows:
                connection.execute(
                    insert(cycles).values(flow_id=flow.id.value, tenant_id=tenant.id.value, outcome="failed", **row)
                )

        migrate_the_rest()

        repository = SqlAlchemyCycleRepositoryAdapter(database, tenant.id)
        assert repository.costs(flow.id.value) == [CycleCost(PLANNED, CallCost(2000, 500, Decimal("0.0031")))]
        later = repository.at(flow.id.value, PLANNED + timedelta(minutes=15))
        assert later is not None
        assert not later.model_called
