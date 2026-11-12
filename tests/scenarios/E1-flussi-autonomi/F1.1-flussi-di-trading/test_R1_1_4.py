import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand
from autotrading.domain.cycles.cycle_record import CycleOutcome
from autotrading.domain.flows.flow_command import FlowCommand
from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.flow_cycles import FlowCycles
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import Lifecycle, add_flow, attempt, flow_named
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


@given(quoted('che il flusso "{name}" è fermo'))
def flow_stopped(platform: Platform, lifecycle: Lifecycle, name: str) -> None:
    assert flow_named(platform, lifecycle.user, name).status is FlowStatus.STOPPED


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
