from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalCommand
from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand
from autotrading.domain.cycles.cycle_record import CycleOutcome
from autotrading.domain.flows.flow_command import FlowCommand
from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.flow_cycles import ACCOUNT, FlowCycles
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import (
    Lifecycle,
    add_flow,
    attempt,
    flow_named,
    hold_position,
    open_assets,
    put_in_status,
)
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.4-avvio-pausa-e-ripresa.feature")


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def platform(flow_cycles: FlowCycles) -> Platform:
    return flow_cycles.platform


@given(quoted('che "{user}" ha il flusso "{name}"'))
def flow_of_user(platform: Platform, lifecycle: Lifecycle, user: str, name: str) -> None:
    add_flow(platform, lifecycle, user, name)


@when(quoted('"{user}" esegue sul flusso "{name}" il comando "{command}"'))
def run_command(platform: Platform, lifecycle: Lifecycle, user: str, name: str, command: str) -> None:
    change = ChangeFlowStatusCommand(flow_named(platform, user, name).id, FlowCommand(command))
    attempt(lifecycle, lambda: platform.use_cases_of(user).change_flow_status.execute(change))


@then(quoted('il comando è rifiutato con il motivo "{reason}"'))
def command_refused(lifecycle: Lifecycle, reason: str) -> None:
    assert str(lifecycle.error) == reason


@when(quoted('"{user}" avvia il flusso "{name}"'))
def start(platform: Platform, lifecycle: Lifecycle, user: str, name: str) -> None:
    change = ChangeFlowStatusCommand(flow_named(platform, user, name).id, FlowCommand.START)
    attempt(lifecycle, lambda: platform.use_cases_of(user).change_flow_status.execute(change))


@then(quoted('il flusso "{name}" esegue il primo ciclo all\'avvio'))
def first_cycle_at_start(flow_cycles: FlowCycles, name: str) -> None:
    started_at = flow_cycles.clock.now()
    flow_cycles.plan_round()
    record = flow_cycles.last_record(name)
    assert (record.planned_at, record.outcome) == (started_at, CycleOutcome.COMPLETED)


@given(quoted('che il flusso "{name}" è attivo con una posizione aperta su "{asset}"'))
def active_with_position(platform: Platform, lifecycle: Lifecycle, name: str, asset: str) -> None:
    put_in_status(platform, lifecycle.user, name, FlowStatus.ACTIVE)
    hold_position(platform, lifecycle.user, ACCOUNT, asset)


@given(
    quoted('che il flusso "{name}" è in pausa con una posizione aperta su "{asset}" e capitale allocato {capital} USDC')
)
def paused_with_position(platform: Platform, lifecycle: Lifecycle, name: str, asset: str, capital: str) -> None:
    user = lifecycle.user
    change = ChangeAllocatedCapitalCommand(
        flow_named(platform, user, name).id, Decimal(capital), platform.user_id_of(user)
    )
    platform.use_cases_of(user).change_allocated_capital.execute(change)
    put_in_status(platform, user, name, FlowStatus.PAUSED)
    hold_position(platform, user, ACCOUNT, asset)


@when(quoted('"{user}" mette in pausa il flusso "{name}"'))
def pause(platform: Platform, lifecycle: Lifecycle, user: str, name: str) -> None:
    change = ChangeFlowStatusCommand(flow_named(platform, user, name).id, FlowCommand.PAUSE)
    attempt(lifecycle, lambda: platform.use_cases_of(user).change_flow_status.execute(change))


@when(quoted('"{user}" riprende il flusso "{name}"'))
def resume(platform: Platform, lifecycle: Lifecycle, user: str, name: str) -> None:
    change = ChangeFlowStatusCommand(flow_named(platform, user, name).id, FlowCommand.RESUME)
    attempt(lifecycle, lambda: platform.use_cases_of(user).change_flow_status.execute(change))


@then(quoted('il flusso "{name}" non esegue cicli'))
def no_cycles(flow_cycles: FlowCycles, platform: Platform, lifecycle: Lifecycle, name: str) -> None:
    flow_id = flow_named(platform, lifecycle.user, name).id.value
    flow_cycles.plan_round()
    assert [record for record in flow_cycles.records.records if record.flow_id == flow_id] == []


@then(quoted('la posizione su "{asset}" resta aperta sull\'exchange'))
def position_still_open(platform: Platform, asset: str) -> None:
    assert asset in open_assets(platform)


@then(quoted('il flusso "{name}" ha ancora la posizione su "{asset}" e capitale allocato {capital} USDC'))
def position_and_capital_kept(platform: Platform, lifecycle: Lifecycle, name: str, asset: str, capital: str) -> None:
    assert asset in open_assets(platform)
    assert flow_named(platform, lifecycle.user, name).configuration.allocated_capital == Decimal(capital)
