import json
from collections.abc import Iterator
from dataclasses import replace
from decimal import Decimal
from typing import cast

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.adapters.inbound.api.strategy_document import StrategyDocument
from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.export_flow_strategy import ExportFlowStrategyCommand
from autotrading.domain.flows.flow_strategy import FlowStrategy
from tests.support.draft_steps import *  # noqa: F403 - the steps of a draft, shared by the features
from tests.support.draft_steps import Draft
from tests.support.flow_steps import KEY, provider_key_registered, valid_command
from tests.support.flows import account_id_of, scenario_catalog
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import Lifecycle, attempt, flow_named
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios(
    "E2-dashboard-e-confronto/F2.5-storico-ed-esportazione/"
    "R2.5.2-esportazione-e-importazione-della-configurazione.feature"
)

# The parts of a flow the file never carries (RF-21.06): where the strategy runs, with how much, and with which keys.
EXCLUDED_KEYS = frozenset({"account", "account_id", "allocated_capital", "capital", "assets", "key", "keys", "cycles"})
IMPORTED_NAME = "importato"
RETIRED_MODEL = "openrouter/modello-ritirato"

type Document = dict[str, object]


class Transfer:
    """The flow the background describes, the file exported from it, and the flows before an import."""

    def __init__(self) -> None:
        self.original = ""
        self.file = ""
        self.flows_before: list[str] = []


@pytest.fixture
def transfer() -> Transfer:
    return Transfer()


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    return platform


def flow_names(platform: Platform, user: str) -> list[str]:
    return [flow.name.value for flow in platform.use_cases_of(user).list_flows.execute()]


def strategy_of(file: str) -> Document:
    return cast(Document, json.loads(file)["strategy"])


def keys_of(document: object) -> Iterator[str]:
    if isinstance(document, dict):
        for key, value in document.items():
            yield key
            yield from keys_of(value)
    if isinstance(document, list):
        for item in document:
            yield from keys_of(item)


def export(platform: Platform, transfer: Transfer, user: str, name: str) -> None:
    command = ExportFlowStrategyCommand(flow_named(platform, user, name).id)
    exported = platform.use_cases_of(user).export_flow_strategy.execute(command)
    transfer.file = StrategyDocument.of(exported.strategy).model_dump_json()


def import_file(
    platform: Platform, lifecycle: Lifecycle, transfer: Transfer, draft: Draft, *, user: str, file: str, name: str
) -> None:
    lifecycle.user = user
    transfer.flows_before = flow_names(platform, user)

    def imported() -> None:
        command = StrategyDocument.model_validate_json(file).command(name)
        draft.name = platform.use_cases_of(user).import_flow_strategy.execute(command).name.value

    attempt(lifecycle, imported)


def file_with(transfer: Transfer, platform: Platform, user: str, change: dict[str, object]) -> str:
    """A file exported from the flow of the background, with a part of its strategy changed or removed (None)."""
    export(platform, transfer, user, transfer.original)
    document = json.loads(transfer.file)
    strategy = document["strategy"]
    for part, value in change.items():
        if value is None:
            del strategy[part]
            continue
        strategy[part] = value
    return json.dumps(document)


@given(
    quoted(
        'che "{user}" ha il flusso "{name}" con asset "{asset}", fonti "{source}" peso {weight}, modello "{model}" '
        'e capitale {capital} USDC sul conto "{account}"'
    )
)
def flow_with_strategy(
    platform: Platform,
    lifecycle: Lifecycle,
    transfer: Transfer,
    user: str,
    name: str,
    *,
    asset: str,
    source: str,
    weight: str,
    model: str,
    capital: str,
    account: str,
) -> None:
    lifecycle.user = user
    transfer.original = name
    provider_key_registered(platform, user, model.partition("/")[0])
    command = replace(
        valid_command(platform, user, name),
        account_id=account_id_of(platform, user, account),
        assets=(asset,),
        model=model,
        sources=(SourceRequest(source, int(weight)),),
        allocated_capital=Decimal(capital),
        instructions="compra solo in tendenza",
    )
    platform.use_cases_of(user).create_flow.execute(command)


@given(quoted('che "{user}" ha esportato il flusso "{name}"'))
@when(quoted('"{user}" esporta il flusso "{name}"'))
def export_flow(platform: Platform, transfer: Transfer, user: str, name: str) -> None:
    export(platform, transfer, user, name)


@then(quoted('ottiene un file con fonti "{source}" peso {weight} e modello "{model}"'))
def file_strategy(transfer: Transfer, source: str, *, weight: str, model: str) -> None:
    strategy = strategy_of(transfer.file)
    sources = cast(list[Document], strategy["sources"])
    assert [(each["name"], each["weight"]) for each in sources] == [(source, int(weight))]
    assert cast(Document, strategy["model"])["name"] == model


@then("il file non contiene conto, capitale, asset né chiavi")
def file_without_account_capital_assets_or_keys(platform: Platform, lifecycle: Lifecycle, transfer: Transfer) -> None:
    original = flow_named(platform, lifecycle.user, transfer.original)
    assert EXCLUDED_KEYS.isdisjoint(keys_of(json.loads(transfer.file)))
    assert str(original.account_id) not in transfer.file
    assert KEY not in transfer.file
    assert set(strategy_of(transfer.file)) == {
        "cycle_minutes",
        "model",
        "sources",
        "instructions",
        "risk_limits",
        "bring_to_minimum",
    }


@when(quoted('"{user}" importa il file con il nome "{name}"'))
def import_exported_file(
    platform: Platform, lifecycle: Lifecycle, transfer: Transfer, draft: Draft, *, user: str, name: str
) -> None:
    import_file(platform, lifecycle, transfer, draft, user=user, file=transfer.file, name=name)
    assert lifecycle.error is None


@given(quoted('che "{user}" ha importato il flusso "{name}"'))
def flow_imported(
    platform: Platform, lifecycle: Lifecycle, transfer: Transfer, draft: Draft, *, user: str, name: str
) -> None:
    export(platform, transfer, user, transfer.original)
    import_file(platform, lifecycle, transfer, draft, user=user, file=transfer.file, name=name)
    assert lifecycle.error is None


@then(
    quoted('esiste il flusso "{name}" nello stato "{status}" alla versione {version} con la strategia di "{original}"')
)
def imported_flow_exists(
    platform: Platform, lifecycle: Lifecycle, draft: Draft, *, name: str, status: str, version: str, original: str
) -> None:
    imported = flow_named(platform, lifecycle.user, name)
    source = flow_named(platform, lifecycle.user, original)
    assert (draft.name, imported.status.value, imported.configuration.version) == (name, status, int(version))
    assert FlowStrategy.of(imported.configuration) == FlowStrategy.of(source.configuration)


@when(quoted('"{user}" importa un file senza modello'))
def import_file_without_model(
    platform: Platform, lifecycle: Lifecycle, transfer: Transfer, draft: Draft, user: str
) -> None:
    file = file_with(transfer, platform, user, {"model": None})
    import_file(platform, lifecycle, transfer, draft, user=user, file=file, name=IMPORTED_NAME)


@when(quoted('"{user}" importa un file con un modello che non è nel catalogo'))
def import_file_with_retired_model(
    platform: Platform, lifecycle: Lifecycle, transfer: Transfer, draft: Draft, user: str
) -> None:
    file = file_with(transfer, platform, user, {"model": {"name": RETIRED_MODEL, "parameters": {}}})
    import_file(platform, lifecycle, transfer, draft, user=user, file=file, name=IMPORTED_NAME)


@then(quoted('l\'importazione è rifiutata con il motivo "{reason}"'))
def import_refused(lifecycle: Lifecycle, reason: str) -> None:
    # The reason comes first; what it refers to, the model of the file, may follow it.
    assert str(lifecycle.error).partition(": ")[0] == reason


@then("nessun flusso viene creato")
def no_flow_created(platform: Platform, lifecycle: Lifecycle, transfer: Transfer) -> None:
    assert flow_names(platform, lifecycle.user) == transfer.flows_before
