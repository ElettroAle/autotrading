from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, RowMapping, Table, func, select, text
from sqlalchemy.exc import ProgrammingError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter, document_of
from autotrading.adapters.outbound.sqlalchemy.tables import flow_versions, flows
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.agent.ports import ModelUse
from autotrading.application.flows.errors import (
    FlowAccountNotFoundError,
    FlowNameInUseError,
    FlowNotFoundError,
    FlowVersionNotFoundError,
)
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow

pytestmark = pytest.mark.integration


def new_account(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    return tenant.id, account.id.value


def rows_of(database: Engine, table: Table, tenant_id: TenantId | None) -> list[RowMapping]:
    # A query written without any tenant filter: only row level security stands between tenants.
    with database.begin() as connection:
        if tenant_id is not None:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return list(connection.execute(select(table)).mappings())


def test_a_saved_flow_reads_back_with_its_whole_configuration(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    configuration = replace(
        a_configuration(assets=("BTC", "ETH"), allocated_capital=Decimal("400.50")),
        model=ModelSelection("openrouter/deepseek-chat", {"temperature": Decimal("0.70"), "reasoning_effort": "alto"}),
        sources=(SourceSelection("notizie", 7, {"hours": 6}), SourceSelection("indicatori")),
        instructions="prudente",
        risk_limits=RiskLimits(3, None, Decimal("12.5")),
    )
    flow = a_flow(tenant_id, account_id=account_id, configuration=configuration)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)

    repository.add(flow)

    assert repository.list() == [flow]


def test_the_flows_are_listed_by_name_with_their_status(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    for name, status in (("gamma", FlowStatus.PAUSED), ("alfa", FlowStatus.STOPPED), ("beta", FlowStatus.ACTIVE)):
        repository.add(a_flow(tenant_id, name=name, status=status, account_id=account_id))

    assert [(flow.name.value, flow.status) for flow in repository.list()] == [
        ("alfa", FlowStatus.STOPPED),
        ("beta", FlowStatus.ACTIVE),
        ("gamma", FlowStatus.PAUSED),
    ]


def test_the_list_carries_the_latest_version_of_each_flow(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow = a_flow(tenant_id, account_id=account_id)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    repository.add(flow)
    second = replace(flow.configuration, version=2, allocated_capital=Decimal(250))
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        connection.execute(
            flow_versions.insert().values(
                flow_id=flow.id.value,
                tenant_id=tenant_id.value,
                version=2,
                configuration={**document_of(flow.configuration), "allocated_capital": "250"},
            )
        )

    assert [listed.configuration for listed in repository.list()] == [second]


def test_the_cycles_find_only_the_flows_of_the_tenant(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    other_tenant, other_account = new_account(database)
    flow = a_flow(tenant_id, account_id=account_id)
    foreign = a_flow(other_tenant, account_id=other_account)
    SqlAlchemyFlowRepositoryAdapter(database, tenant_id).add(flow)
    SqlAlchemyFlowRepositoryAdapter(database, other_tenant).add(foreign)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)

    assert (repository.exists(flow.id.value), repository.exists(foreign.id.value)) == (True, False)
    assert not repository.exists(uuid4())


def test_the_agent_sees_each_flow_with_the_provider_of_its_model_and_whether_it_runs(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    for name, status in (("alfa", FlowStatus.ACTIVE), ("beta", FlowStatus.STOPPED)):
        repository.add(a_flow(tenant_id, name=name, status=status, account_id=account_id))

    assert repository.model_uses() == (
        ModelUse("alfa", "openrouter", running=True),
        ModelUse("beta", "openrouter", running=False),
    )


def test_a_name_is_in_use_only_by_a_flow_not_archived(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    repository.add(a_flow(tenant_id, name="alfa", account_id=account_id))
    repository.add(a_flow(tenant_id, name="beta", status=FlowStatus.ARCHIVED, account_id=account_id))

    assert repository.name_in_use(FlowName("alfa"))
    assert not repository.name_in_use(FlowName("beta"))
    repository.add(a_flow(tenant_id, name="beta", account_id=account_id))


def test_the_database_refuses_a_second_flow_with_the_same_name(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    repository.add(a_flow(tenant_id, name="alfa", account_id=account_id))

    with pytest.raises(FlowNameInUseError):
        repository.add(a_flow(tenant_id, name="alfa", account_id=account_id))

    assert len(rows_of(database, flows, tenant_id)) == 1
    assert len(rows_of(database, flow_versions, tenant_id)) == 1


def test_a_tenant_never_sees_nor_adds_the_flows_of_another(database: Engine) -> None:
    anna, anna_account = new_account(database)
    bruno, _ = new_account(database)
    SqlAlchemyFlowRepositoryAdapter(database, anna).add(a_flow(anna, name="alfa", account_id=anna_account))
    bruno_flows = SqlAlchemyFlowRepositoryAdapter(database, bruno)

    assert bruno_flows.list() == []
    assert not bruno_flows.name_in_use(FlowName("alfa"))
    with pytest.raises(CrossTenantAccessError):
        bruno_flows.add(a_flow(anna, name="beta", account_id=anna_account))
    assert rows_of(database, flows, bruno) == []
    assert rows_of(database, flow_versions, bruno) == []
    assert len(rows_of(database, flows, anna)) == 1


def test_a_flow_cannot_run_on_the_account_of_another_tenant(database: Engine) -> None:
    _, anna_account = new_account(database)
    bruno, _ = new_account(database)

    with pytest.raises(FlowAccountNotFoundError):
        SqlAlchemyFlowRepositoryAdapter(database, bruno).add(a_flow(bruno, account_id=anna_account))

    assert rows_of(database, flows, bruno) == []


def test_a_configuration_version_is_never_changed_nor_deleted(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    SqlAlchemyFlowRepositoryAdapter(database, tenant_id).add(a_flow(tenant_id, account_id=account_id))

    for statement in ("UPDATE flow_versions SET version = 9", "DELETE FROM flow_versions"):
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
            with pytest.raises(ProgrammingError, match="permission denied"):
                connection.execute(text(statement))


def test_a_flow_is_read_by_its_id_with_the_version_in_force(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    flow = a_flow(tenant_id, account_id=account_id)
    repository.add(flow)
    repository.add(a_flow(tenant_id, name="beta", account_id=account_id))
    second = flow.reconfigured(a_configuration(assets=("ETH",)))

    repository.add_version(second)

    assert repository.get(flow.id) == second
    assert repository.version(flow.id, 1) == flow.configuration
    assert repository.version(flow.id, 2) == second.configuration
    assert len(rows_of(database, flow_versions, tenant_id)) == 3


def test_a_status_change_is_saved(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    flow = a_flow(tenant_id, account_id=account_id)
    repository.add(flow)

    repository.change_status(replace(flow, status=FlowStatus.ARCHIVED))

    assert repository.get(flow.id).status == FlowStatus.ARCHIVED
    assert not repository.name_in_use(flow.name)


def test_a_flow_or_version_missing_or_of_another_tenant_is_not_found(database: Engine) -> None:
    anna, anna_account = new_account(database)
    bruno, _ = new_account(database)
    flow = a_flow(anna, account_id=anna_account)
    SqlAlchemyFlowRepositoryAdapter(database, anna).add(flow)
    bruno_flows = SqlAlchemyFlowRepositoryAdapter(database, bruno)

    for action in (
        lambda: bruno_flows.get(flow.id),
        lambda: bruno_flows.version(flow.id, 1),
        lambda: bruno_flows.change_status(replace(flow, tenant_id=bruno, status=FlowStatus.ACTIVE)),
        lambda: bruno_flows.add_version(replace(flow, tenant_id=bruno)),
        lambda: bruno_flows.get(FlowId.new()),
    ):
        with pytest.raises(FlowNotFoundError):
            action()
    with pytest.raises(CrossTenantAccessError):
        bruno_flows.add_version(flow)
    with pytest.raises(FlowVersionNotFoundError):
        SqlAlchemyFlowRepositoryAdapter(database, anna).version(flow.id, 2)
    assert SqlAlchemyFlowRepositoryAdapter(database, anna).get(flow.id) == flow
