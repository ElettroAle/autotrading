from dataclasses import replace
from datetime import timedelta

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.duplicate_flow import DuplicateFlowCommand
from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.read_free_capital import ReadFreeCapitalCommand
from autotrading.domain.flows.free_capital import FreeCapital
from tests.support.draft_steps import *  # noqa: F403 - the steps of a draft, shared by the features
from tests.support.draft_steps import Draft
from tests.support.flow_cycles import FlowCycles
from tests.support.flow_steps import provider_key_registered, valid_command
from tests.support.flows import account_id_of
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import Lifecycle, attempt, flow_named
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E2-dashboard-e-confronto/F2.4-confronto-tra-flussi/R2.4.1-duplicazione-di-un-flusso.feature")


class Duplication:
    """The free capital of an account before time passed."""

    def __init__(self) -> None:
        self.free_capital: FreeCapital | None = None


@pytest.fixture
def duplication() -> Duplication:
    return Duplication()


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def platform(flow_cycles: FlowCycles) -> Platform:
    return flow_cycles.platform


def free_capital_of(platform: Platform, user: str, account: str) -> FreeCapital:
    command = ReadFreeCapitalCommand(account_id_of(platform, user, account))
    return platform.use_cases_of(user).read_free_capital.execute(command)


def duplicate(platform: Platform, lifecycle: Lifecycle, draft: Draft, user: str, name: str) -> None:
    flow_id = flow_named(platform, lifecycle.user, name).id

    def duplicated() -> None:
        draft.name = platform.use_cases_of(user).duplicate_flow.execute(DuplicateFlowCommand(flow_id)).name.value

    attempt(lifecycle, duplicated)


@given(
    quoted(
        'che "{user}" ha il flusso "{name}" sul conto "{account}" con asset "{asset}", fonti "{source}" peso {weight} '
        'e modello "{model}"'
    )
)
def flow_with_strategy(
    platform: Platform,
    lifecycle: Lifecycle,
    user: str,
    name: str,
    *,
    account: str,
    asset: str,
    source: str,
    weight: str,
    model: str,
) -> None:
    lifecycle.user = user
    provider_key_registered(platform, user, model.partition("/")[0])
    command = replace(
        valid_command(platform, user, name),
        account_id=account_id_of(platform, user, account),
        assets=(asset,),
        model=model,
        sources=(SourceRequest(source, int(weight)),),
    )
    platform.use_cases_of(user).create_flow.execute(command)


@given(quoted('che "{user}" ha anche il conto "{account}"'))
def other_account(platform: Platform, user: str, account: str) -> None:
    account_id_of(platform, user, account)


@given(quoted('che "{user}" ha duplicato il flusso "{name}"'))
@when(quoted('"{user}" duplica il flusso "{name}"'))
def duplicate_flow(platform: Platform, lifecycle: Lifecycle, draft: Draft, user: str, name: str) -> None:
    duplicate(platform, lifecycle, draft, user, name)
    assert lifecycle.error is None


@when(quoted('"{user}" chiede di duplicare il flusso "{name}"'))
def ask_duplicate(platform: Platform, lifecycle: Lifecycle, draft: Draft, user: str, name: str) -> None:
    duplicate(platform, lifecycle, draft, user, name)


@then(quoted('esiste il flusso "{name}" nello stato "{status}" alla versione {version}'))
def copy_exists(
    platform: Platform, lifecycle: Lifecycle, draft: Draft, *, name: str, status: str, version: str
) -> None:
    copy = flow_named(platform, lifecycle.user, name)
    assert (draft.name, copy.status.value, copy.configuration.version) == (name, status, int(version))


@then(quoted('ha fonti "{source}" peso {weight} e modello "{model}"'))
def copy_strategy(
    platform: Platform, lifecycle: Lifecycle, draft: Draft, source: str, *, weight: str, model: str
) -> None:
    configuration = flow_named(platform, lifecycle.user, draft.name).configuration
    original = flow_named(platform, lifecycle.user, draft.name.removesuffix(" (copia)")).configuration
    assert [(each.name, each.weight) for each in configuration.sources] == [(source, int(weight))]
    assert configuration.sources == original.sources
    assert configuration.model == original.model
    assert configuration.model.name == model
    assert (configuration.instructions, configuration.risk_limits, configuration.cycle_interval) == (
        original.instructions,
        original.risk_limits,
        original.cycle_interval,
    )


@when(quoted('passa un intervallo intero del flusso "{name}"'))
def interval_passes(
    flow_cycles: FlowCycles, platform: Platform, lifecycle: Lifecycle, duplication: Duplication, name: str
) -> None:
    flow = flow_named(platform, lifecycle.user, name)
    duplication.free_capital = free_capital_of(platform, lifecycle.user, "principale")
    flow_cycles.plan_round()
    flow_cycles.clock.current = flow_cycles.clock.now() + timedelta(minutes=flow.configuration.cycle_interval.minutes)
    flow_cycles.plan_round()


@then(quoted('il flusso "{name}" non ha cicli'))
def no_cycles(flow_cycles: FlowCycles, platform: Platform, lifecycle: Lifecycle, name: str) -> None:
    flow_id = flow_named(platform, lifecycle.user, name).id.value
    assert [record for record in flow_cycles.records.records if record.flow_id == flow_id] == []


@then(quoted('il capitale libero del conto "{account}" non cambia'))
def free_capital_unchanged(platform: Platform, lifecycle: Lifecycle, duplication: Duplication, account: str) -> None:
    assert duplication.free_capital is not None
    assert free_capital_of(platform, lifecycle.user, account) == duplication.free_capital


@then(quoted('l\'avvio è rifiutato con il motivo "{reason}"'))
def start_refused(lifecycle: Lifecycle, reason: str) -> None:
    assert str(lifecycle.error) == reason


@then(quoted('il flusso "{name}" resta nello stato "{status}"'))
def status_kept(platform: Platform, lifecycle: Lifecycle, name: str, status: str) -> None:
    assert flow_named(platform, lifecycle.user, name).status.value == status


@then("la richiesta è rifiutata come flusso inesistente")
def request_refused_as_missing(lifecycle: Lifecycle) -> None:
    assert isinstance(lifecycle.error, FlowNotFoundError)
