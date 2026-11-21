"""R6.4.8 on the use cases: the flow read alone answers an archived flow too, with its status, so its page opens in
read only (Bug 690, ADR pagina-del-flusso-archiviato-in-sola-lettura). playwright-bdd runs the page on the dashboard.
"""

from dataclasses import replace

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.get_flow import GetFlowCommand
from autotrading.domain.flows.flow import Flow
from tests.support.flow_steps import provider_key_registered, valid_command
from tests.support.flows import scenario_catalog
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import Lifecycle, flow_named
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios(
    "E6-piattaforma-e-operativita/F6.4-dashboard-su-mobile/R6.4.8-prossima-esecuzione-nella-panoramica/api/R6.4.8-prossima-esecuzione-nella-panoramica.feature"
)


class Reading:
    """The flow the user read alone."""

    def __init__(self) -> None:
        self.flow: Flow | None = None


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    return platform


@pytest.fixture
def reading() -> Reading:
    return Reading()


@given(quoted('che "{user}" ha il flusso "{name}" con un ciclo ogni {minutes} minuti'))
def flow_with_interval(platform: Platform, lifecycle: Lifecycle, user: str, name: str, minutes: str) -> None:
    lifecycle.user = user
    provider_key_registered(platform, user, "openrouter")
    command = replace(valid_command(platform, user, name), cycle_minutes=int(minutes))
    platform.use_cases_of(user).create_flow.execute(command)


@when(quoted('"{user}" legge il flusso "{name}"'))
def read_flow(platform: Platform, reading: Reading, user: str, name: str) -> None:
    command = GetFlowCommand(flow_named(platform, user, name).id)
    reading.flow = platform.use_cases_of(user).get_flow.execute(command)


@then(quoted('il flusso letto è nello stato "{status}"'))
def flow_read_in_status(reading: Reading, status: str) -> None:
    assert reading.flow is not None
    assert reading.flow.status.value == status
