import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand
from autotrading.domain.flows.flow_command import FlowCommand
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import PositionLeftOpen
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.flows import ACCOUNT, scenario_catalog
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import (
    Lifecycle,
    add_flow,
    flow_named,
    hold_position,
    open_assets,
    put_in_status,
    stop,
)
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.5-stop-di-un-flusso.feature")


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    return platform


@given(quoted('che "{user}" ha il flusso "{name}" attivo con posizioni aperte su "{first}" e "{second}"'))
def active_flow_with_positions(
    platform: Platform, lifecycle: Lifecycle, user: str, name: str, *, first: str, second: str
) -> None:
    add_flow(platform, lifecycle, user, name, assets=(first, second))
    put_in_status(platform, user, name, FlowStatus.ACTIVE)
    for asset in (first, second):
        hold_position(platform, user, ACCOUNT, asset)


@given(quoted('che il flusso "{name}" è in pausa'))
def flow_paused(platform: Platform, lifecycle: Lifecycle, name: str) -> None:
    command = ChangeFlowStatusCommand(flow_named(platform, lifecycle.user, name).id, FlowCommand.PAUSE)
    platform.use_cases_of(lifecycle.user).change_flow_status.execute(command)


@given(quoted('che un ciclo del flusso "{name}" è in corso'))
def cycle_running(platform: Platform, lifecycle: Lifecycle, name: str) -> None:
    platform.running_cycles.running.add(flow_named(platform, lifecycle.user, name).id)


@given(quoted('che il flusso "{name}" è fermo'))
def flow_brought_to_stop(platform: Platform, lifecycle: Lifecycle, name: str) -> None:
    stop(platform, lifecycle, lifecycle.user, name)
    assert flow_named(platform, lifecycle.user, name).status == FlowStatus.STOPPED


@when(quoted('"{user}" ferma il flusso "{name}"'))
def user_stops(platform: Platform, lifecycle: Lifecycle, user: str, name: str) -> None:
    stop(platform, lifecycle, user, name)


@when(quoted('"{user}" avvia il flusso "{name}"'))
def user_starts(platform: Platform, user: str, name: str) -> None:
    command = ChangeFlowStatusCommand(flow_named(platform, user, name).id, FlowCommand.START)
    platform.use_cases_of(user).change_flow_status.execute(command)


@then(quoted('sull\'exchange il flusso "{name}" non ha posizioni aperte'))
def no_positions_of_flow(platform: Platform, lifecycle: Lifecycle, name: str) -> None:
    assets = set(flow_named(platform, lifecycle.user, name).configuration.assets)
    assert open_assets(platform) & assets == set()


@then(quoted('il flusso "{name}" non esegue cicli'))
def no_cycles(platform: Platform, lifecycle: Lifecycle, name: str) -> None:
    # Only an active flow runs cycles (R1.2.1): a stopped one is never among those the executor schedules.
    flows = platform.use_cases_of(lifecycle.user).list_flows.execute()
    assert name not in [flow.name.value for flow in flows if flow.status == FlowStatus.ACTIVE]


@then("il ciclo in corso si conclude")
def cycle_ended(platform: Platform, lifecycle: Lifecycle) -> None:
    (flow,) = platform.use_cases_of(lifecycle.user).list_flows.execute()
    assert [flow_id for flow_id, _ in platform.running_cycles.ended] == [flow.id]
    assert platform.running_cycles.running == set()


@then(quoted('dopo il ciclo le posizioni del flusso "{name}" vengono chiuse'))
def closed_after_cycle(platform: Platform, lifecycle: Lifecycle, name: str) -> None:
    flow = flow_named(platform, lifecycle.user, name)
    ((ended, sent_before_end),) = platform.running_cycles.ended
    closings = [order.coin for order in platform.order_exchange.sent[sent_before_end:] if order.reduce_only]
    assert (ended, sent_before_end) == (flow.id, 0)
    assert closings == list(flow.configuration.assets)
    assert open_assets(platform) == set()


@then(quoted('l\'esito dello stop riporta la posizione su "{asset}" rimasta aperta con il motivo "{reason}"'))
def stop_reports_left_open(lifecycle: Lifecycle, asset: str, reason: str) -> None:
    assert lifecycle.stop is not None
    assert lifecycle.stop.left_open == (PositionLeftOpen(asset, reason),)
