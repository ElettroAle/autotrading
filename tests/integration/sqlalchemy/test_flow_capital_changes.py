from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import ProgrammingError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import flow_capital_changes
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow

pytestmark = pytest.mark.integration

USER = UserId("oid-anna")
FIRST = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
SECOND = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def new_account(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    return tenant.id, account.id.value


def test_a_capital_change_saves_the_next_version_and_its_history_together(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    flow = a_flow(tenant_id, account_id=account_id, configuration=a_configuration(allocated_capital=Decimal(400)))
    repository.add(flow)
    raised = flow.with_capital(Decimal("700.25"))
    lowered = raised.with_capital(Decimal(200))

    repository.add_capital_change(raised, CapitalChange(flow.id, FIRST, Decimal(400), Decimal("700.25"), USER))
    repository.add_capital_change(lowered, CapitalChange(flow.id, SECOND, Decimal("700.25"), Decimal(200), USER))

    assert repository.get(flow.id) == lowered
    assert repository.version(flow.id, 2).allocated_capital == Decimal("700.25")
    assert repository.capital_changes(flow.id) == (
        CapitalChange(flow.id, FIRST, Decimal(400), Decimal("700.25"), USER),
        CapitalChange(flow.id, SECOND, Decimal("700.25"), Decimal(200), USER),
    )


def test_a_flow_without_changes_has_an_empty_history(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    flow = a_flow(tenant_id, account_id=account_id)
    repository.add(flow)

    assert repository.capital_changes(flow.id) == ()


def test_the_history_of_another_tenant_is_never_read_nor_written(database: Engine) -> None:
    anna, account_id = new_account(database)
    bruno, _ = new_account(database)
    flow = a_flow(anna, account_id=account_id)
    SqlAlchemyFlowRepositoryAdapter(database, anna).add(flow)
    theirs = SqlAlchemyFlowRepositoryAdapter(database, bruno)
    change = CapitalChange(flow.id, FIRST, Decimal(100), Decimal(200), USER)

    with pytest.raises(FlowNotFoundError):
        theirs.capital_changes(flow.id)
    with pytest.raises(CrossTenantAccessError):
        theirs.add_capital_change(flow.with_capital(Decimal(200)), change)
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(bruno.value), True)))
        assert list(connection.execute(select(flow_capital_changes))) == []


def test_a_recorded_change_is_never_changed_nor_deleted(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    flow = a_flow(tenant_id, account_id=account_id)
    repository.add(flow)
    repository.add_capital_change(
        flow.with_capital(Decimal(200)), CapitalChange(flow.id, FIRST, Decimal(100), Decimal(200), USER)
    )

    for statement in ("UPDATE flow_capital_changes SET new_capital = 9", "DELETE FROM flow_capital_changes"):
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
            with pytest.raises(ProgrammingError, match="permission denied"):
                connection.execute(text(statement))
