from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import ProgrammingError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import flow_capital_changes
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow

pytestmark = pytest.mark.integration

USER = UserId("oid-anna")
FIRST = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
SECOND = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
EVER = TimeWindow()


def a_change(flow_id: FlowId, at: datetime, previous: Decimal, new: Decimal) -> CapitalChange:
    reason = CapitalChangeReason.INCREASE if new > previous else CapitalChangeReason.REDUCTION
    return CapitalChange(flow_id, at, previous, new, USER, reason, abs(new - previous), value_before=previous)


def a_cash_out(flow_id: FlowId, previous: Decimal, new: Decimal, value: Decimal) -> CapitalChange:
    return CapitalChange(
        flow_id,
        SECOND,
        previous,
        new,
        USER,
        CapitalChangeReason.CASH_OUT,
        value - new,
        value_before=value,
        cashed_profit=value - previous,
    )


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

    repository.add_capital_change(raised, a_change(flow.id, FIRST, Decimal(400), Decimal("700.25")))
    repository.add_capital_change(lowered, a_change(flow.id, SECOND, Decimal("700.25"), Decimal(200)))

    assert repository.get(flow.id) == lowered
    assert repository.version(flow.id, 2).allocated_capital == Decimal("700.25")
    assert repository.capital_changes((flow.id,), EVER, 10) == (
        a_change(flow.id, SECOND, Decimal("700.25"), Decimal(200)),
        a_change(flow.id, FIRST, Decimal(400), Decimal("700.25")),
    )


def test_a_cash_out_keeping_the_capital_is_recorded_on_the_version_in_force(database: Engine) -> None:
    # ADR incasso-dei-profitti: reason, amount freed, value before and profit cashed out travel with the change.
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    flow = a_flow(tenant_id, account_id=account_id, configuration=a_configuration(allocated_capital=Decimal(500)))
    repository.add(flow)
    cash_out = a_cash_out(flow.id, Decimal(500), Decimal(500), Decimal("618.5"))

    repository.add_capital_change(flow, cash_out)

    assert [version.number for version in repository.versions(flow.id)] == [1]
    assert repository.capital_changes((flow.id,), EVER, 10) == (cash_out,)


def test_the_profits_cashed_out_sum_up_by_flow(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    flow = a_flow(tenant_id, account_id=account_id, configuration=a_configuration(allocated_capital=Decimal(500)))
    never = a_flow(tenant_id, name="beta", account_id=account_id)
    repository.add(flow)
    repository.add(never)
    lowered = flow.with_capital(Decimal(400))
    repository.add_capital_change(lowered, a_cash_out(flow.id, Decimal(500), Decimal(400), Decimal(618)))
    repository.add_capital_change(lowered, a_cash_out(flow.id, Decimal(400), Decimal(400), Decimal("430.5")))

    assert repository.cashed_profits_of((flow.id, never.id)) == {flow.id: Decimal("148.5")}
    assert repository.cashed_profits_of(()) == {}
    assert SqlAlchemyFlowRepositoryAdapter(database, new_account(database)[0]).cashed_profits_of((flow.id,)) == {}


def test_a_flow_without_changes_has_an_empty_history(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    flow = a_flow(tenant_id, account_id=account_id)
    repository.add(flow)

    assert repository.capital_changes((flow.id,), EVER, 10) == ()
    assert repository.count_capital_changes((flow.id,), EVER) == 0
    assert repository.capital_changes((), EVER, 10) == ()
    assert repository.count_capital_changes((), EVER) == 0


def test_the_most_recent_changes_of_the_flows_asked_in_the_window_come_newest_first(database: Engine) -> None:
    # R3.4.2, ADR storico-delle-variazioni-di-capitale: the page of a flow or of an account reads its newest changes.
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    alfa = a_flow(tenant_id, account_id=account_id, configuration=a_configuration(allocated_capital=Decimal(100)))
    beta = a_flow(tenant_id, name="beta", account_id=account_id)
    gamma = a_flow(tenant_id, name="gamma", account_id=account_id)
    for flow in (alfa, beta, gamma):
        repository.add(flow)
    early = a_change(alfa.id, datetime(2026, 11, 10, 9, tzinfo=UTC), Decimal(100), Decimal(200))
    middle = a_change(beta.id, datetime(2026, 11, 14, 9, tzinfo=UTC), Decimal(100), Decimal(300))
    late = a_change(alfa.id, datetime(2026, 11, 15, 9, tzinfo=UTC), Decimal(200), Decimal(400))
    elsewhere = a_change(gamma.id, datetime(2026, 11, 15, 10, tzinfo=UTC), Decimal(100), Decimal(500))
    repository.add_capital_change(alfa.with_capital(Decimal(200)), early)
    repository.add_capital_change(beta.with_capital(Decimal(300)), middle)
    repository.add_capital_change(alfa.with_capital(Decimal(200)).with_capital(Decimal(400)), late)
    repository.add_capital_change(gamma.with_capital(Decimal(500)), elsewhere)
    asked = (alfa.id, beta.id)
    window = TimeWindow.of_days(date(2026, 11, 14), date(2026, 11, 16))

    assert repository.capital_changes(asked, EVER, 10) == (late, middle, early)
    assert repository.capital_changes(asked, EVER, 2) == (late, middle)
    assert repository.capital_changes(asked, window, 10) == (late, middle)
    assert repository.count_capital_changes(asked, EVER) == 3
    assert repository.count_capital_changes(asked, window) == 2


def test_the_history_of_another_tenant_is_never_read_nor_written(database: Engine) -> None:
    anna, account_id = new_account(database)
    bruno, _ = new_account(database)
    flow = a_flow(anna, account_id=account_id)
    SqlAlchemyFlowRepositoryAdapter(database, anna).add(flow)
    theirs = SqlAlchemyFlowRepositoryAdapter(database, bruno)
    change = a_change(flow.id, FIRST, Decimal(100), Decimal(200))

    SqlAlchemyFlowRepositoryAdapter(database, anna).add_capital_change(flow.with_capital(Decimal(200)), change)

    assert theirs.capital_changes((flow.id,), EVER, 10) == ()
    assert theirs.count_capital_changes((flow.id,), EVER) == 0
    with pytest.raises(CrossTenantAccessError):
        theirs.add_capital_change(flow.with_capital(Decimal(200)), change)
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(bruno.value), True)))
        assert list(connection.execute(select(flow_capital_changes))) == []
    assert SqlAlchemyFlowRepositoryAdapter(database, anna).count_capital_changes((flow.id,), EVER) == 1


def test_a_recorded_change_is_never_changed_nor_deleted(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    repository = SqlAlchemyFlowRepositoryAdapter(database, tenant_id)
    flow = a_flow(tenant_id, account_id=account_id)
    repository.add(flow)
    repository.add_capital_change(flow.with_capital(Decimal(200)), a_change(flow.id, FIRST, Decimal(100), Decimal(200)))

    for statement in ("UPDATE flow_capital_changes SET new_capital = 9", "DELETE FROM flow_capital_changes"):
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
            with pytest.raises(ProgrammingError, match="permission denied"):
                connection.execute(text(statement))
