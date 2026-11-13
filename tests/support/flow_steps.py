"""Steps shared by the features that create flows: one valid configuration, changed by what a step names.

A scenario module imports them all; pytest-bdd keeps each step as a fixture of this module.
"""

from dataclasses import replace
from decimal import Decimal

import pytest
from pytest_bdd import given, then, when

from autotrading.application.agent.register_provider_key import RegisterProviderKeyCommand
from autotrading.application.flows.create_flow import CreateFlowCommand, SourceRequest
from autotrading.application.flows.read_free_capital import ReadFreeCapitalCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.flow import Flow
from tests.support.flows import OPENROUTER_MODEL, account_id_of
from tests.support.platform import HYPERLIQUID, Platform
from tests.support.steps import quoted

KEY = "K-REGISTERED"


class Creation:
    """The flow a scenario creates: the user, how many flows of that name existed, and the answer or the refusal."""

    def __init__(self) -> None:
        self.user = ""
        self.flows_before = 0
        self.flow: Flow | None = None
        self.error: AutotradingError | None = None


@pytest.fixture
def creation() -> Creation:
    return Creation()


def flows_named(platform: Platform, user: str, name: str) -> list[Flow]:
    return [flow for flow in platform.use_cases_of(user).list_flows.execute() if flow.name.value == name]


def valid_command(platform: Platform, user: str, name: str) -> CreateFlowCommand:
    return CreateFlowCommand(
        name=name,
        account_id=account_id_of(platform, user),
        assets=("BTC",),
        model=OPENROUTER_MODEL,
        allocated_capital=Decimal(100),
        max_leverage=5,
        max_margin_exposure_percent=Decimal(10),
    )


def create(platform: Platform, creation: Creation, user: str, command: CreateFlowCommand) -> None:
    creation.user = user
    creation.flows_before = len(flows_named(platform, user, command.name))
    try:
        creation.flow = platform.use_cases_of(user).create_flow.execute(command)
    except AutotradingError as error:
        creation.error = error


def flow_of(creation: Creation, platform: Platform, name: str) -> Flow:
    (flow,) = flows_named(platform, creation.user, name)
    return flow


def names(listed: str) -> tuple[str, ...]:
    return tuple(name.strip() for name in listed.split(","))


@given(quoted('che "{user}" ha registrato la chiave del fornitore "{provider}"'))
def provider_key_registered(platform: Platform, user: str, provider: str) -> None:
    platform.use_cases_of(user).register_provider_key.execute(RegisterProviderKeyCommand(provider, KEY))


@when(
    quoted(
        '"{user}" crea il flusso "{name}" sul conto "{account}" con asset "{assets}", modello "{model}", '
        'fonti "{sources}", leva massima {leverage}, esposizione massima del margine {margin}% '
        "e capitale allocato {capital} USDC"
    )
)
def create_complete_flow(
    platform: Platform,
    creation: Creation,
    user: str,
    name: str,
    *,
    account: str,
    assets: str,
    model: str,
    sources: str,
    leverage: str,
    margin: str,
    capital: str,
) -> None:
    command = CreateFlowCommand(
        name=name,
        account_id=account_id_of(platform, user, account),
        assets=names(assets),
        model=model,
        allocated_capital=Decimal(capital),
        max_leverage=int(leverage),
        max_margin_exposure_percent=Decimal(margin),
        sources=tuple(SourceRequest(source) for source in names(sources)),
    )
    create(platform, creation, user, command)


@when(quoted('"{user}" crea il flusso "{name}" senza indicare l\'intervallo di ciclo'))
def create_without_interval(platform: Platform, creation: Creation, user: str, name: str) -> None:
    create(platform, creation, user, valid_command(platform, user, name))


@when(quoted('"{user}" crea il flusso "{name}" con intervallo di ciclo {minutes} minuti'))
def create_with_interval(platform: Platform, creation: Creation, user: str, name: str, minutes: str) -> None:
    create(platform, creation, user, replace(valid_command(platform, user, name), cycle_minutes=int(minutes)))


@when(quoted('"{user}" crea il flusso "{name}" con modello "{model}"'))
def create_with_model(platform: Platform, creation: Creation, user: str, name: str, model: str) -> None:
    create(platform, creation, user, replace(valid_command(platform, user, name), model=model))


@when(quoted('"{user}" crea il flusso "{name}" con fonte "{source}"'))
def create_with_source(platform: Platform, creation: Creation, user: str, name: str, source: str) -> None:
    command = replace(valid_command(platform, user, name), sources=(SourceRequest(source),))
    create(platform, creation, user, command)


@when(quoted('"{user}" crea il flusso "{name}" con asset "{asset}" non negoziabile sull\'exchange del conto'))
def create_with_untradable_asset(platform: Platform, creation: Creation, user: str, name: str, asset: str) -> None:
    assert asset not in platform.markets[HYPERLIQUID].assets
    create(platform, creation, user, replace(valid_command(platform, user, name), assets=(asset,)))


@when(quoted('"{user}" crea il flusso "{name}" con nessun asset'))
def create_without_assets(platform: Platform, creation: Creation, user: str, name: str) -> None:
    create(platform, creation, user, replace(valid_command(platform, user, name), assets=()))


@when(quoted('"{user}" crea il flusso "{name}" con nessuna leva massima'))
def create_without_leverage(platform: Platform, creation: Creation, user: str, name: str) -> None:
    create(platform, creation, user, replace(valid_command(platform, user, name), max_leverage=None))


@when(quoted('"{user}" crea il flusso "{name}" con nessun limite di esposizione per operazione'))
def create_without_exposure(platform: Platform, creation: Creation, user: str, name: str) -> None:
    command = replace(valid_command(platform, user, name), max_margin_exposure_percent=None)
    create(platform, creation, user, command)


@when(quoted('"{user}" crea il flusso "{name}" con capitale allocato {capital} USDC'))
def create_with_capital(platform: Platform, creation: Creation, user: str, name: str, capital: str) -> None:
    command = replace(valid_command(platform, user, name), allocated_capital=Decimal(capital))
    create(platform, creation, user, command)


@when(quoted('"{user}" crea il flusso "{name}" con il nome "{other}" già usato da un suo flusso'))
def create_with_used_name(platform: Platform, creation: Creation, user: str, name: str, other: str) -> None:
    platform.use_cases_of(user).create_flow.execute(valid_command(platform, user, other))
    create(platform, creation, user, valid_command(platform, user, name))


@when(quoted('"{user}" crea il flusso "{name}" con modello "{model}" e temperatura {value}'))
def create_with_temperature(
    platform: Platform, creation: Creation, user: str, name: str, *, model: str, value: str
) -> None:
    command = replace(valid_command(platform, user, name), model=model, model_parameters={"temperature": value})
    create(platform, creation, user, command)


@when(quoted('"{user}" crea il flusso "{name}" con modello "{model}" e livello di ragionamento "{value}"'))
def create_with_reasoning(
    platform: Platform, creation: Creation, user: str, name: str, *, model: str, value: str
) -> None:
    command = replace(valid_command(platform, user, name), model=model, model_parameters={"reasoning_effort": value})
    create(platform, creation, user, command)


@when(quoted('"{user}" crea il flusso "{name}" con modello "{model}" senza parametri'))
def create_with_default_parameters(platform: Platform, creation: Creation, user: str, name: str, model: str) -> None:
    create(platform, creation, user, replace(valid_command(platform, user, name), model=model))


@then(quoted('la creazione è rifiutata con il motivo "{reason}"'))
def creation_refused(creation: Creation, reason: str) -> None:
    assert creation.flow is None
    assert str(creation.error) == reason


@then(quoted('"{user}" non ha il flusso "{name}"'))
def flow_not_added(platform: Platform, creation: Creation, user: str, name: str) -> None:
    assert len(flows_named(platform, user, name)) == creation.flows_before


@then(quoted('"{user}" ha il flusso "{name}" nello stato "{status}"'))
def flow_in_status(platform: Platform, user: str, name: str, status: str) -> None:
    assert [flow.status.value for flow in flows_named(platform, user, name)] == [status]


@then(quoted('il flusso "{name}" ha la versione di configurazione {version}'))
def flow_version(platform: Platform, creation: Creation, name: str, version: str) -> None:
    assert flow_of(creation, platform, name).configuration.version == int(version)


@then(quoted('il flusso "{name}" ha l\'intervallo di ciclo di {minutes} minuti'))
def flow_interval(platform: Platform, creation: Creation, name: str, minutes: str) -> None:
    assert flow_of(creation, platform, name).configuration.cycle_interval.minutes == int(minutes)


@then(quoted('il flusso "{name}" usa la temperatura {value}'))
def flow_temperature(platform: Platform, creation: Creation, name: str, value: str) -> None:
    assert flow_of(creation, platform, name).configuration.model.parameters["temperature"] == Decimal(value)


@then(quoted('il capitale libero del conto "{account}" è {amount} USDC'))
def free_capital(platform: Platform, creation: Creation, account: str, amount: str) -> None:
    command = ReadFreeCapitalCommand(account_id_of(platform, creation.user, account))
    assert str(platform.use_cases_of(creation.user).read_free_capital.execute(command)) == f"{amount} USDC"
