from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select, text

from autotrading.adapters.outbound.sqlalchemy.emergency_closing_log import SqlAlchemyEmergencyClosingLogAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import emergency_closings
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.emergency_closing import EmergencyClosing, EmergencyScope, FlowEmergencyOutcome
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.stop_outcome import PositionLeftOpen
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

pytestmark = pytest.mark.integration

CLOSED_AT = datetime(2026, 11, 16, 9, 30, tzinfo=UTC)


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def a_closing(tenant_id: TenantId) -> EmergencyClosing:
    outcome = FlowEmergencyOutcome(FlowId.new(), "alfa", ("ETH",), (PositionLeftOpen("BTC", "Order rejected"),))
    return EmergencyClosing(tenant_id, EmergencyScope(account_id=uuid4()), CLOSED_AT, (outcome,))


def rows_seen_by(database: Engine, tenant_id: TenantId | None) -> int:
    with database.begin() as connection:
        if tenant_id is not None:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return int(connection.execute(text("SELECT count(*) FROM emergency_closings")).scalar_one())


def test_a_closing_is_recorded_with_its_instant_scope_and_outcome(database: Engine) -> None:
    tenant_id = new_tenant(database)
    closing = a_closing(tenant_id)

    SqlAlchemyEmergencyClosingLogAdapter(database, tenant_id).record(closing)

    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        row = connection.execute(select(emergency_closings)).mappings().one()
    assert (row["closed_at"], row["scope_kind"], row["scope_id"]) == (CLOSED_AT, "account", closing.scope.account_id)
    assert row["outcome"][0]["left_open"] == [{"asset": "BTC", "reason": "Order rejected"}]


def test_a_query_without_any_filter_sees_only_the_closings_of_its_tenant(database: Engine) -> None:
    tenant_id, other_tenant = new_tenant(database), new_tenant(database)
    SqlAlchemyEmergencyClosingLogAdapter(database, tenant_id).record(a_closing(tenant_id))

    assert rows_seen_by(database, tenant_id) == 1
    assert rows_seen_by(database, other_tenant) == 0
    assert rows_seen_by(database, None) == 0


def test_a_tenant_cannot_record_the_closing_of_another_tenant(database: Engine) -> None:
    tenant_id, other_tenant = new_tenant(database), new_tenant(database)

    with pytest.raises(CrossTenantAccessError):
        SqlAlchemyEmergencyClosingLogAdapter(database, other_tenant).record(a_closing(tenant_id))

    assert rows_seen_by(database, tenant_id) == 0
