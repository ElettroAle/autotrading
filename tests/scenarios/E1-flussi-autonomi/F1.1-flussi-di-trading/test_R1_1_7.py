from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalCommand
from autotrading.application.flows.free_capital import ReadFreeCapitalCommand
from autotrading.application.flows.list_capital_changes import ListCapitalChangesCommand
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.free_capital import amount_text
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.flows import account_id_of, scenario_catalog
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import Lifecycle, add_flow, attempt, flow_named, hold_position
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.7-capitale-allocato.feature")


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    return platform


@given(quoted('che "{user}" ha il conto "{account}" con saldo {balance} USDC'))
def account_with_balance(platform: Platform, lifecycle: Lifecycle, user: str, account: str, balance: str) -> None:
    lifecycle.user = user
    account_id_of(platform, user, account, Decimal(balance))


@given(
    quoted(
        'che "{user}" ha il flusso "{name}" sul conto "{account}" con capitale allocato {capital} USDC '
        "e {margin} USDC impegnati come margine"
    )
)
def flow_with_margin(
    platform: Platform, lifecycle: Lifecycle, user: str, name: str, *, account: str, capital: str, margin: str
) -> None:
    flow = add_flow(platform, lifecycle, user, name, account=account, capital=Decimal(capital))
    (asset,) = flow.configuration.assets
    hold_position(platform, user, account, asset, Decimal(margin))


@when(quoted('"{user}" porta il capitale allocato del flusso "{name}" a {capital} USDC'))
def change_capital(platform: Platform, lifecycle: Lifecycle, user: str, name: str, capital: str) -> None:
    flow_id = flow_named(platform, user, name).id
    command = ChangeAllocatedCapitalCommand(flow_id, Decimal(capital), platform.user_id_of(user))
    attempt(lifecycle, lambda: platform.use_cases_of(user).change_allocated_capital.execute(command))


@then(quoted('il flusso "{name}" ha capitale allocato {capital} USDC'))
def allocated_capital(platform: Platform, lifecycle: Lifecycle, name: str, capital: str) -> None:
    assert flow_named(platform, lifecycle.user, name).configuration.allocated_capital == Decimal(capital)


@then(quoted('il capitale libero del conto "{account}" è {amount} USDC'))
def account_free_capital(platform: Platform, lifecycle: Lifecycle, account: str, amount: str) -> None:
    command = ReadFreeCapitalCommand(account_id_of(platform, lifecycle.user, account))
    capital = platform.use_cases_of(lifecycle.user).read_free_capital.execute(command)
    assert (amount_text(capital.amount), capital.currency) == (amount, "USDC")


@then(quoted('la variazione da {previous} a {new} USDC è registrata nello storico del flusso "{name}"'))
def change_recorded(platform: Platform, lifecycle: Lifecycle, previous: str, new: str, name: str) -> None:
    flow = flow_named(platform, lifecycle.user, name)
    changes = platform.use_cases_of(lifecycle.user).list_capital_changes.execute(ListCapitalChangesCommand(flow.id))
    user_id = platform.user_id_of(lifecycle.user)
    assert changes == (CapitalChange(flow.id, platform.now, Decimal(previous), Decimal(new), user_id),)


@then(quoted('la variazione è rifiutata con il motivo "{reason}"'))
def change_refused(lifecycle: Lifecycle, reason: str) -> None:
    assert str(lifecycle.error) == reason
