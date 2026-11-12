import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.accounts.remove_account import RemoveAccountCommand
from autotrading.domain.accounts.errors import FlowPositionsLeftOpenError
from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.flows import scenario_catalog
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import Lifecycle, add_flow, attempt, hold_position, put_in_status
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.8-rimozione-di-un-conto-con-flussi.feature")


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    return platform


@given(quoted('che "{user}" ha il conto "{account}" con il flusso "{name}" attivo e una posizione aperta su "{asset}"'))
def account_with_active_flow(
    platform: Platform, lifecycle: Lifecycle, user: str, account: str, *, name: str, asset: str
) -> None:
    add_flow(platform, lifecycle, user, name, account=account, assets=(asset,))
    put_in_status(platform, user, name, FlowStatus.ACTIVE)
    hold_position(platform, user, account, asset)


def remove(platform: Platform, lifecycle: Lifecycle, user: str, account: str, *, confirmed: bool) -> None:
    account_id = platform.account_named(user, account).id
    command = RemoveAccountCommand(account_id, platform.user_id_of(user), confirmed=confirmed)
    attempt(lifecycle, lambda: platform.use_cases_of(user).remove_account.execute(command))


@when(quoted('"{user}" rimuove il conto "{account}" senza confermare'))
def remove_without_confirming(platform: Platform, lifecycle: Lifecycle, user: str, account: str) -> None:
    remove(platform, lifecycle, user, account, confirmed=False)


@when(quoted('"{user}" rimuove il conto "{account}" confermando'))
def remove_confirming(platform: Platform, lifecycle: Lifecycle, user: str, account: str) -> None:
    remove(platform, lifecycle, user, account, confirmed=True)


@then(quoted('la rimozione è sospesa con il motivo "{reason}"'))
def removal_suspended(lifecycle: Lifecycle, reason: str) -> None:
    assert str(lifecycle.error) == reason


@then(quoted('il conto "{account}" non compare più tra i conti di "{user}"'))
def account_gone(platform: Platform, account: str, user: str) -> None:
    assert account not in [each.name.value for each in platform.accounts_of(user)]


@then(quoted('il conto "{account}" resta tra i conti di "{user}"'))
def account_kept(platform: Platform, account: str, user: str) -> None:
    assert account in [each.name.value for each in platform.accounts_of(user)]


@then(quoted('il flusso "{name}" compare tra i flussi archiviati di "{user}"'))
def flow_among_archived(platform: Platform, name: str, user: str) -> None:
    archived = platform.use_cases_of(user).list_flows.execute(archived=True)
    assert [flow.name.value for flow in archived if flow.status == FlowStatus.ARCHIVED] == [name]


@then(quoted('l\'esito riporta la posizione su "{asset}" rimasta aperta con il motivo "{reason}"'))
def removal_reports_left_open(lifecycle: Lifecycle, asset: str, reason: str) -> None:
    assert isinstance(lifecycle.error, FlowPositionsLeftOpenError)
    assert lifecycle.error.positions == ((asset, reason),)
