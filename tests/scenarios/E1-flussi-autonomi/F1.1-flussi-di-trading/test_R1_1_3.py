import threading

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.compare_flow_versions import CompareFlowVersionsCommand
from autotrading.application.flows.get_flow_version import GetFlowVersionCommand
from autotrading.domain.flows.configuration_difference import ConfigurationDifference
from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.flows.flow_status import FlowStatus
from tests.fakes.model_call import HELD_SECONDS
from tests.support.flow_cycles import FlowCycles
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.flow_steps import names, provider_key_registered
from tests.support.flows import ANTHROPIC_MODEL, OPENROUTER_MODEL, account_id_of
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import Lifecycle, add_flow, flow_named, modify, put_in_status
from tests.support.platform import Platform
from tests.support.steps import quoted


class Comparison:
    def __init__(self) -> None:
        self.differences: tuple[ConfigurationDifference, ...] = ()


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def platform(flow_cycles: FlowCycles) -> Platform:
    return flow_cycles.platform


@pytest.fixture
def comparison() -> Comparison:
    return Comparison()


scenarios("E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.3-modifica-versionata-della-configurazione.feature")


@given(
    quoted('che "{user}" ha il flusso "{name}" attivo con asset "{assets}" e modello "{model}" alla versione {version}')
)
def active_flow(
    platform: Platform, lifecycle: Lifecycle, user: str, name: str, *, assets: str, model: str, version: str
) -> None:
    # The keys of both providers the scenarios name: a model is usable only with the key of its provider (R1.4.1).
    provider_key_registered(platform, user, "openrouter")
    provider_key_registered(platform, user, "anthropic")
    flow = add_flow(platform, lifecycle, user, name, assets=names(assets))
    put_in_status(platform, user, name, FlowStatus.ACTIVE)
    assert (flow.configuration.model.name, flow.configuration.version) == (model, int(version))


@given(quoted('che il flusso "{name}" ha la versione {version} con modello "{model}"'))
def second_version(platform: Platform, lifecycle: Lifecycle, name: str, version: str, model: str) -> None:
    modify(platform, lifecycle, lifecycle.user, name, model=model)
    assert flow_named(platform, lifecycle.user, name).configuration.version == int(version)


@when(quoted('"{user}" confronta le versioni {first} e {second} del flusso "{name}"'))
def compare(platform: Platform, comparison: Comparison, user: str, *, first: str, second: str, name: str) -> None:
    command = CompareFlowVersionsCommand(flow_named(platform, user, name).id, int(first), int(second))
    comparison.differences = platform.use_cases_of(user).compare_flow_versions.execute(command)


@when(quoted('"{user}" modifica l\'intervallo di ciclo del flusso "{name}" in {minutes} minuti'))
def modify_interval(platform: Platform, lifecycle: Lifecycle, user: str, name: str, minutes: str) -> None:
    modify(platform, lifecycle, user, name, cycle_minutes=int(minutes))


@when(quoted('"{user}" modifica il conto del flusso "{name}"'))
def modify_account(platform: Platform, lifecycle: Lifecycle, user: str, name: str) -> None:
    modify(platform, lifecycle, user, name, account_id=account_id_of(platform, user, "test-2"))


@then(quoted('il flusso "{name}" ha la versione di configurazione {version} con modello "{model}"'))
def version_in_force(platform: Platform, lifecycle: Lifecycle, name: str, version: str, model: str) -> None:
    configuration = flow_named(platform, lifecycle.user, name).configuration
    assert (configuration.version, configuration.model.name) == (int(version), model)


@then(quoted('la versione {version} del flusso "{name}" resta consultabile con modello "{model}"'))
def previous_version(platform: Platform, lifecycle: Lifecycle, version: str, name: str, model: str) -> None:
    command = GetFlowVersionCommand(flow_named(platform, lifecycle.user, name).id, int(version))
    assert platform.use_cases_of(lifecycle.user).get_flow_version.execute(command).model.name == model


@then(quoted('il confronto riporta solo la differenza sul modello, da "{before}" a "{after}"'))
def only_the_model(comparison: Comparison, before: str, after: str) -> None:
    assert comparison.differences == (ConfigurationDifference("modello", before, after),)


@then(quoted('il flusso "{name}" resta alla versione di configurazione {version}'))
def version_unchanged(platform: Platform, lifecycle: Lifecycle, name: str, version: str) -> None:
    assert flow_named(platform, lifecycle.user, name).configuration.version == int(version)


@given(quoted('che un ciclo del flusso "{name}" è in corso con la versione {version}'))
def cycle_in_progress(
    flow_cycles: FlowCycles, platform: Platform, lifecycle: Lifecycle, name: str, version: str
) -> None:
    assert flow_named(platform, lifecycle.user, name).configuration.version == int(version)
    flow_cycles.model.gate = threading.Event()
    flow_cycles.running = threading.Thread(target=flow_cycles.plan_round, daemon=True)
    flow_cycles.running.start()
    assert flow_cycles.model.entered.wait(HELD_SECONDS)


@then(quoted("il ciclo in corso si conclude con la versione {version}"))
def cycle_ends_with_version(flow_cycles: FlowCycles, version: str) -> None:
    assert flow_cycles.model.gate is not None
    flow_cycles.model.gate.set()
    assert flow_cycles.running is not None
    flow_cycles.running.join(HELD_SECONDS)
    [call] = flow_cycles.model.calls
    assert call.model == model_of_version(version)
    assert flow_cycles.records.records[-1].outcome is CycleOutcome.COMPLETED


@then(quoted('il ciclo successivo del flusso "{name}" usa la versione {version}'))
def next_cycle_uses_version(flow_cycles: FlowCycles, name: str, version: str) -> None:
    flow_cycles.model.gate = None
    flow_cycles.run(name, "10:15")
    assert flow_cycles.model.calls[-1].model == model_of_version(version)


def model_of_version(version: str) -> str:
    """The model the agent was called with: version 1 has DeepSeek, version 2 Claude."""
    return {"1": OPENROUTER_MODEL, "2": ANTHROPIC_MODEL}[version]
