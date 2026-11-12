from dataclasses import replace

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.flow_steps import Creation, create, names, valid_command
from tests.support.flows import account_id_of, scenario_catalog
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import Lifecycle, flow_named
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.2-regola-di-conflitto-sugli-asset.feature")


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    return platform


@given(quoted('che "{user}" ha i conti "{first}" e "{second}"'))
def two_accounts(platform: Platform, user: str, first: str, second: str) -> None:
    account_id_of(platform, user, first)
    account_id_of(platform, user, second)


@when(quoted('"{user}" crea il flusso "{name}" sul conto "{account}" con asset "{assets}"'))
def create_on_account(
    platform: Platform, creation: Creation, user: str, name: str, *, account: str, assets: str
) -> None:
    command = replace(
        valid_command(platform, user, name), account_id=account_id_of(platform, user, account), assets=names(assets)
    )
    create(platform, creation, user, command)


@then(quoted('il flusso "{name}" ha ancora gli asset "{assets}"'))
def flow_assets(platform: Platform, lifecycle: Lifecycle, name: str, assets: str) -> None:
    assert flow_named(platform, lifecycle.user, name).configuration.assets == names(assets)
