from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select, text

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.exit_plan_repository import SqlAlchemyExitPlanRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration

PLAN = ExitPlan(Decimal("63000.5"), Decimal(58500), "chiusura a 4 ore sotto 59000")


def new_flow(database: Engine) -> tuple[TenantId, FlowId]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, name=f"flusso-{uuid4()}", account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return tenant.id, flow.id


def test_a_saved_plan_reads_back_whole_and_without_rounding(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    plans = SqlAlchemyExitPlanRepositoryAdapter(database, tenant_id)

    plans.save(flow_id, "BTC", PLAN)

    assert plans.current(flow_id, "BTC") == PLAN
    assert plans.current(flow_id, "ETH") is None


def test_an_empty_plan_reads_back_empty(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    plans = SqlAlchemyExitPlanRepositoryAdapter(database, tenant_id)

    plans.save(flow_id, "BTC", ExitPlan())

    assert plans.current(flow_id, "BTC") == ExitPlan()


def test_a_new_plan_replaces_the_one_in_force(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    plans = SqlAlchemyExitPlanRepositoryAdapter(database, tenant_id)
    plans.save(flow_id, "BTC", PLAN)

    plans.save(flow_id, "BTC", ExitPlan(stop=Decimal(59000)))

    assert plans.current(flow_id, "BTC") == ExitPlan(stop=Decimal(59000))


def test_a_removed_plan_is_no_longer_in_force(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    plans = SqlAlchemyExitPlanRepositoryAdapter(database, tenant_id)
    plans.save(flow_id, "BTC", PLAN)
    plans.save(flow_id, "ETH", PLAN)

    plans.remove(flow_id, "BTC")
    plans.remove(flow_id, "SOL")

    assert (plans.current(flow_id, "BTC"), plans.current(flow_id, "ETH")) == (None, PLAN)


def test_the_plans_of_a_tenant_are_invisible_to_another_tenant(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)
    SqlAlchemyExitPlanRepositoryAdapter(database, tenant_id).save(flow_id, "BTC", PLAN)

    assert SqlAlchemyExitPlanRepositoryAdapter(database, other_tenant).current(flow_id, "BTC") is None
    SqlAlchemyExitPlanRepositoryAdapter(database, other_tenant).remove(flow_id, "BTC")
    assert SqlAlchemyExitPlanRepositoryAdapter(database, tenant_id).current(flow_id, "BTC") == PLAN


def test_a_query_without_any_filter_sees_only_the_rows_of_its_tenant(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)
    SqlAlchemyExitPlanRepositoryAdapter(database, tenant_id).save(flow_id, "BTC", PLAN)

    for tenant in (other_tenant, None):
        with database.begin() as connection:
            if tenant is not None:
                connection.execute(select(func.set_config("app.tenant_id", str(tenant.value), True)))
            assert connection.execute(text("SELECT count(*) FROM flow_exit_plans")).scalar_one() == 0


def test_a_tenant_cannot_save_a_plan_on_the_flow_of_another_tenant(database: Engine) -> None:
    _, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)

    with pytest.raises(CrossTenantAccessError):
        SqlAlchemyExitPlanRepositoryAdapter(database, other_tenant).save(flow_id, "BTC", PLAN)
