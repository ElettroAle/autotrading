"""ADR migrazione-delle-fonti-al-modello-ad-adapter: the flows saved before the adapters get a new version with every
source passed to its adapter, weights and parameters unchanged; the versions before stay as they were, and every value
collected gets its adapter (R4.1.1).
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, insert, select, text

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter, document_of
from autotrading.adapters.outbound.sqlalchemy.tables import flow_versions
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.flow import Flow
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow
from tests.support.postgres import database_migrated_to

pytestmark = pytest.mark.integration

BEFORE_THE_ADAPTERS = "0049"
OLD_SOURCES = [
    {"name": "sentiment-alternative-me", "weight": 4, "parameters": {}},
    {"name": "sentiment-coinmarketcap", "weight": 6, "parameters": {}},
]
PLANNED = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)


def a_flow_before_the_adapters(database: Engine) -> tuple[TenantId, Flow, dict[str, object]]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, "conto", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    # The second version as the platform saved it before the adapters: a weight and parameters per source.
    old_document = {**document_of(a_configuration()), "sources": OLD_SOURCES}
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant.id.value), True)))
        connection.execute(
            insert(flow_versions).values(
                flow_id=flow.id.value, version=2, tenant_id=tenant.id.value, configuration=old_document
            )
        )
        connection.execute(
            text(
                "INSERT INTO source_samples (tenant_id, flow_id, cycle_planned_at, source, asset, reference_at,"
                " collected_at, sample_values) VALUES (:tenant, :flow, :at, 'sentiment-coinmarketcap', NULL, :at,"
                ' :at, \'{"valore": "29"}\')'
            ),
            {"tenant": tenant.id.value, "flow": flow.id.value, "at": PLANNED},
        )
    return tenant.id, flow, old_document


def documents_of(database: Engine, tenant_id: TenantId) -> dict[int, dict[str, object]]:
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        rows = connection.execute(select(flow_versions.c.version, flow_versions.c.configuration)).all()
    return {version: configuration for version, configuration in rows}


def test_a_flow_before_the_adapters_gets_a_new_version_with_the_same_weights(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_ADAPTERS) as (database, migrate_the_rest):
        tenant_id, flow, old_document = a_flow_before_the_adapters(database)

        migrate_the_rest()

        documents = documents_of(database, tenant_id)
        assert sorted(documents) == [1, 2, 3]
        assert documents[2] == old_document
        assert documents[3]["sources"] == [
            {
                "name": "sentiment",
                "adapters": [
                    {"name": "alternative.me", "weight": 4, "parameters": {}},
                    {"name": "CoinMarketCap", "weight": 6, "parameters": {}},
                ],
            }
        ]
        assert documents[3]["migrated_from"] == "sources-v1"
        current = SqlAlchemyFlowRepositoryAdapter(database, tenant_id).get(flow.id).configuration
        assert current.version == 3
        assert [(adapter.name, adapter.weight) for adapter in current.sources[0].adapters] == [
            ("alternative.me", 4),
            ("CoinMarketCap", 6),
        ]


def test_a_value_collected_before_the_adapters_gets_its_source_and_adapter(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_ADAPTERS) as (database, migrate_the_rest):
        tenant_id, _, _ = a_flow_before_the_adapters(database)

        migrate_the_rest()

        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
            samples = connection.execute(text("SELECT source, adapter FROM source_samples")).all()
        assert [tuple(sample) for sample in samples] == [("sentiment", "CoinMarketCap")]
