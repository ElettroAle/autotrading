import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand
from autotrading.domain.flows.flow_command import FlowCommand
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.flows import scenario_catalog
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import Lifecycle, add_flow, attempt, flow_named
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.4-avvio-pausa-e-ripresa.feature")


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    return platform


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
