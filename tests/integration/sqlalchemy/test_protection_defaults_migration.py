"""ADR stop-loss-e-take-profit-predefiniti-del-flusso: the versions saved before the defaults existed read with a
stop loss of 5% and no take profit after the migration, without a new version.
"""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter, document_of
from autotrading.adapters.outbound.sqlalchemy.tables import flow_versions
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow
from tests.support.postgres import database_migrated_to

pytestmark = pytest.mark.integration

BEFORE_THE_DEFAULTS = "0027"
DEFAULT_KEYS = ("default_stop_loss_percent", "default_take_profit_percent")


def test_a_version_saved_before_the_defaults_reads_with_a_stop_loss_of_five_percent(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_DEFAULTS) as (database, migrate_the_rest):
        tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
        SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
        account = an_account(tenant.id, "conto", SealedCredentials(1, b"\x00sealed"))
        SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
        flows = SqlAlchemyFlowRepositoryAdapter(database, tenant.id)
        flow = a_flow(tenant.id, account_id=account.id.value)
        flows.add(flow)
        # The second version as the platform saved it before the defaults: without their keys.
        old_document = {key: value for key, value in document_of(a_configuration()).items() if key not in DEFAULT_KEYS}
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant.id.value), True)))
            connection.execute(
                insert(flow_versions).values(
                    flow_id=flow.id.value, version=2, tenant_id=tenant.id.value, configuration=old_document
                )
            )

        migrate_the_rest()

        assert flows.get(flow.id).configuration.protection_defaults == ProtectionDefaults()
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant.id.value), True)))
            versions = connection.execute(select(func.count()).select_from(flow_versions)).scalar_one()
        assert versions == 2
