from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios

from autotrading.domain.sources.source_catalog import SOURCE_CATALOG
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.flows import account_id_of, scenario_catalog
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.1-creazione-di-un-flusso.feature")


@pytest.fixture
def platform() -> Platform:
    return Platform()


@given(quoted('che "{user}" ha il conto "{account}" con saldo {balance} USDC e nessun flusso'))
def account_without_flows(platform: Platform, user: str, account: str, balance: str) -> None:
    account_id_of(platform, user, account, Decimal(balance))
    assert platform.use_cases_of(user).list_flows.execute() == []


@given(quoted('che il catalogo dei modelli contiene "{model}"'))
def catalog_with_model(platform: Platform, model: str) -> None:
    platform.model_catalog = scenario_catalog()
    assert model in [definition.name for definition in platform.model_catalog.models]


@given(quoted('che il catalogo delle fonti contiene "{first}" e "{second}"'))
def catalog_with_sources(first: str, second: str) -> None:
    assert {first, second} <= {source.name for source in SOURCE_CATALOG.sources}
