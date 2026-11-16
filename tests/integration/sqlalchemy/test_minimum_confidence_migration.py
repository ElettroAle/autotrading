"""ADR confidenza-nella-decisione-e-confidenza-minima: the versions saved before the minimum confidence existed read
without one after the migration, without a new version.
"""

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter, document_of
from autotrading.adapters.outbound.sqlalchemy.tables import flow_versions
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow
from tests.support.postgres import database_migrated_to

pytestmark = pytest.mark.integration

BEFORE_THE_MINIMUM_CONFIDENCE = "0030"
MINIMUM_CONFIDENCE = "minimum_confidence"


def test_a_version_saved_before_the_minimum_confidence_reads_without_one(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_MINIMUM_CONFIDENCE) as (database, migrate_the_rest):
        tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
        SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
        account = an_account(tenant.id, "conto", SealedCredentials(1, b"\x00sealed"))
        SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
        flows = SqlAlchemyFlowRepositoryAdapter(database, tenant.id)
        flow = a_flow(tenant.id, account_id=account.id.value)
        flows.add(flow)
        # The second version as the platform saved it before the minimum confidence: without its key.
        saved = document_of(a_configuration())
        old_document = {key: value for key, value in saved.items() if key != MINIMUM_CONFIDENCE}
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant.id.value), True)))
            connection.execute(
                insert(flow_versions).values(
                    flow_id=flow.id.value, version=2, tenant_id=tenant.id.value, configuration=old_document
                )
            )

        migrate_the_rest()

        assert flows.get(flow.id).configuration.minimum_confidence is None
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant.id.value), True)))
            versions = connection.execute(select(func.count()).select_from(flow_versions)).scalar_one()
        assert versions == 2


def test_a_minimum_confidence_saved_after_the_migration_reads_back(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_MINIMUM_CONFIDENCE) as (database, migrate_the_rest):
        migrate_the_rest()
        tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
        SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
        account = an_account(tenant.id, "conto", SealedCredentials(1, b"\x00sealed"))
        SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
        flows = SqlAlchemyFlowRepositoryAdapter(database, tenant.id)
        configuration = replace(a_configuration(), minimum_confidence=MinimumConfidence(60))
        flow = a_flow(tenant.id, account_id=account.id.value, configuration=configuration)
        flows.add(flow)

        assert flows.get(flow.id).configuration.minimum_confidence == MinimumConfidence(60)
