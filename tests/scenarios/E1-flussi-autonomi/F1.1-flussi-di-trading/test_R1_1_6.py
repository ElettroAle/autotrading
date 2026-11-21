from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.archive_flow import ArchiveFlowCommand
from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand
from autotrading.application.flows.list_closed_positions import ListClosedPositionsCommand
from autotrading.application.flows.list_cycles import ListCyclesCommand
from autotrading.application.flows.list_flow_versions import ListFlowVersionsCommand
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.trade_side import TradeSide
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.flows import ANTHROPIC_MODEL, account_id_of, scenario_catalog
from tests.support.history import a_closed_position
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import Lifecycle, add_flow, attempt, flow_named, modify
from tests.support.platform import STARTED_AT, Platform
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


@when(quoted('"{user}" avvia il flusso "{name}"'))
def start(platform: Platform, lifecycle: Lifecycle, user: str, name: str) -> None:
    command = ChangeFlowStatusCommand(flow_named(platform, user, name).id, FlowAction.START)
    attempt(lifecycle, lambda: platform.use_cases_of(user).change_flow_status.execute(command))


@then(quoted('l\'avvio è rifiutato con il motivo "{reason}"'))
def start_refused(lifecycle: Lifecycle, reason: str) -> None:
    assert str(lifecycle.error) == reason


@given(quoted('che il flusso "{name}" ha {versions} versioni della configurazione e una posizione chiusa su "{asset}"'))
def flow_with_versions_and_closed_position(
    platform: Platform, lifecycle: Lifecycle, name: str, versions: str, asset: str
) -> None:
    modify(platform, lifecycle, lifecycle.user, name, assets=("BTC", "ETH"))
    flow = flow_named(platform, lifecycle.user, name)
    assert flow.configuration.version == int(versions)
    position = replace(a_closed_position(STARTED_AT, asset), tenant_id=flow.tenant_id, flow_id=flow.id)
    platform.closed_positions.positions.append(position)


@then(quoted('le {versions} versioni della configurazione del flusso "{name}" restano consultabili'))
def versions_still_consultable(platform: Platform, lifecycle: Lifecycle, versions: str, name: str) -> None:
    command = ListFlowVersionsCommand(flow_named(platform, lifecycle.user, name).id)
    listed = platform.use_cases_of(lifecycle.user).list_flow_versions.execute(command)
    assert len(listed) == int(versions)


@then(quoted('la posizione chiusa su "{asset}" del flusso "{name}" resta consultabile'))
def closed_position_still_consultable(platform: Platform, lifecycle: Lifecycle, asset: str, name: str) -> None:
    command = ListClosedPositionsCommand(flow_named(platform, lifecycle.user, name).id.value)
    positions = platform.use_cases_of(lifecycle.user).list_closed_positions.execute(command).positions
    assert [(position.asset, position.side) for position in positions] == [(asset, TradeSide.LONG)]
