from datetime import timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.cycles.list_cycles import ListCyclesCommand
from autotrading.application.flows.archive_flow import ArchiveFlowCommand
from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.flows import ANTHROPIC_MODEL, account_id_of, scenario_catalog
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import Lifecycle, add_flow, attempt, flow_named, modify
from tests.support.platform import Platform
from tests.support.record_steps import a_recorded_cycle
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.6-archiviazione-di-un-flusso.feature")


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    return platform


@given(quoted('che "{user}" ha il conto "{account}" con saldo {balance} USDC'))
def account_with_balance(platform: Platform, user: str, account: str, balance: str) -> None:
    account_id_of(platform, user, account, Decimal(balance))


@given(
    quoted(
        'che "{user}" ha il flusso "{name}" sul conto "{account}" con capitale allocato {capital} USDC '
        "e {cycles} cicli registrati"
    )
)
def flow_with_cycles(
    platform: Platform, lifecycle: Lifecycle, user: str, name: str, *, account: str, capital: str, cycles: str
) -> None:
    flow = add_flow(platform, lifecycle, user, name, account=account, capital=Decimal(capital))
    for number in range(int(cycles)):
        platform.cycles.record(a_recorded_cycle(flow.id.value, "10:00", back=timedelta(minutes=15 * number)))


@when(quoted('"{user}" archivia il flusso "{name}"'))
def archive(platform: Platform, lifecycle: Lifecycle, user: str, name: str) -> None:
    command = ArchiveFlowCommand(flow_named(platform, user, name).id)
    attempt(lifecycle, lambda: platform.use_cases_of(user).archive_flow.execute(command))


@when(quoted('"{user}" modifica il modello del flusso "{name}"'))
def modify_any_model(platform: Platform, lifecycle: Lifecycle, user: str, name: str) -> None:
    modify(platform, lifecycle, user, name, model=ANTHROPIC_MODEL)


@then(quoted('l\'archiviazione è rifiutata con il motivo "{reason}"'))
def archiving_refused(lifecycle: Lifecycle, reason: str) -> None:
    assert str(lifecycle.error) == reason


@then(quoted('il flusso "{name}" non compare tra i flussi in uso di "{user}"'))
def flow_not_in_use(platform: Platform, name: str, user: str) -> None:
    assert name not in [flow.name.value for flow in platform.use_cases_of(user).list_flows.execute()]


@then(quoted('il flusso "{name}" compare tra i flussi archiviati di "{user}"'))
def flow_among_archived(platform: Platform, name: str, user: str) -> None:
    archived = platform.use_cases_of(user).list_flows.execute(archived=True)
    assert [flow.name.value for flow in archived if flow.status == FlowStatus.ARCHIVED] == [name]


@then(quoted('i {count} cicli del flusso "{name}" restano consultabili'))
def cycles_still_consultable(platform: Platform, lifecycle: Lifecycle, count: str, name: str) -> None:
    command = ListCyclesCommand(flow_named(platform, lifecycle.user, name).id.value)
    assert len(platform.use_cases_of(lifecycle.user).list_cycles.execute(command).cycles) == int(count)
