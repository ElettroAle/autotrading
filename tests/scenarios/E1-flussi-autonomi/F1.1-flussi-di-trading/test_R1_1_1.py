from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios

from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.activity import a_fill
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.flows import a_configuration, a_flow, account_id_of, scenario_catalog
from tests.support.platform import Platform
from tests.support.source_selections import PLATFORM_CATALOG
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.1-creazione-di-un-flusso.feature")

# The account of the background belongs to her.
OWNER = "anna"


@pytest.fixture
def platform() -> Platform:
    return Platform()


@given(quoted('che "{user}" ha il conto "{account}" con saldo {balance} USDC e nessun flusso'))
def account_without_flows(platform: Platform, user: str, account: str, balance: str) -> None:
    account_id_of(platform, user, account, Decimal(balance))
    assert platform.use_cases_of(user).list_flows.execute() == []


@given(
    quoted(
        'che sul conto "{account}" c\'è anche il flusso attivo "{name}" con capitale allocato {capital} USDC e '
        "valore complessivo {value} USDC"
    )
)
def other_flow_worth(platform: Platform, account: str, name: str, capital: str, value: str) -> None:
    # ADR capitale-libero-al-netto-del-valore-dei-flussi: what the other flow earned stays its own.
    account_id = account_id_of(platform, OWNER, account)
    configuration = a_configuration(assets=("SOL",), allocated_capital=Decimal(capital))
    tenant_id = platform.tenant_of(OWNER)
    flow = a_flow(tenant_id, name=name, status=FlowStatus.ACTIVE, account_id=account_id, configuration=configuration)
    platform.flows.flows.append(flow)
    earned = a_fill("SOL", None, realized_pnl=Decimal(value) - Decimal(capital), size=Decimal(0))
    platform.ledger.add(account_id, flow.id, earned)
    assert platform.use_cases_of(OWNER).list_flows.execute() == [flow]


@given(quoted('che il catalogo dei modelli contiene "{model}"'))
def catalog_with_model(platform: Platform, model: str) -> None:
    platform.model_catalog = scenario_catalog()
    assert model in [definition.name for definition in platform.model_catalog.models]


@given(quoted('che il catalogo delle fonti contiene "{first}" e "{second}"'))
def catalog_with_sources(first: str, second: str) -> None:
    assert {first, second} <= {source.name for source in PLATFORM_CATALOG.sources}
