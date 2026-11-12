"""Steps shared by the features on the life of a flow: statuses, changes of configuration, archiving.

A scenario module imports them all, beside those of flow creation; pytest-bdd keeps each step as a fixture of
that module.
"""

from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal

import pytest
from pytest_bdd import given, then, when

from autotrading.application.flows.archive_flow import ArchiveFlowCommand
from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.application.flows.stop_flow import StopFlowCommand
from autotrading.bootstrap import TradingAccessFromAccounts
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_command import FlowCommand
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import StopOutcome
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.support.activity import a_position, an_activity
from tests.support.flow_steps import names, provider_key_registered, valid_command
from tests.support.flows import account_id_of
from tests.support.platform import Platform
from tests.support.steps import quoted

# The commands that bring a stopped flow to each status, the way the user would.
COMMANDS_TO = {
    FlowStatus.STOPPED: (),
    FlowStatus.ACTIVE: (FlowCommand.START,),
    FlowStatus.PAUSED: (FlowCommand.START, FlowCommand.PAUSE),
}


class Lifecycle:
    """The user of the scenario, the refusal of what they asked if any, and the outcome of a stop."""

    """The user of the scenario and the refusal of what they asked, if any."""

    def __init__(self) -> None:
        self.user = ""
        self.error: AutotradingError | None = None
        self.stop: StopOutcome | None = None


@pytest.fixture
def lifecycle() -> Lifecycle:
    return Lifecycle()


def flow_named(platform: Platform, user: str, name: str) -> Flow:
    use_cases = platform.use_cases_of(user)
    (flow,) = [
        flow
        for flow in [*use_cases.list_flows.execute(), *use_cases.list_flows.execute(archived=True)]
        if flow.name.value == name
    ]
    return flow


def add_flow(
    platform: Platform,
    lifecycle: Lifecycle,
    user: str,
    name: str,
    *,
    account: str = "test-1",
    assets: tuple[str, ...] = ("BTC",),
    capital: Decimal = Decimal(100),
) -> Flow:
    lifecycle.user = user
    # Every flow needs a model, and a model is usable only with the key of its provider (R1.4.1).
    if not platform.use_cases_of(user).list_provider_keys.execute():
        provider_key_registered(platform, user, "openrouter")
    command = replace(
        valid_command(platform, user, name),
        account_id=account_id_of(platform, user, account),
        assets=assets,
        allocated_capital=capital,
    )
    return platform.use_cases_of(user).create_flow.execute(command)


def put_in_status(platform: Platform, user: str, name: str, status: FlowStatus) -> None:
    use_cases = platform.use_cases_of(user)
    flow_id = flow_named(platform, user, name).id
    if status == FlowStatus.ARCHIVED:
        use_cases.archive_flow.execute(ArchiveFlowCommand(flow_id))
        return
    for command in COMMANDS_TO[status]:
        use_cases.change_flow_status.execute(ChangeFlowStatusCommand(flow_id, command))


def hold_position(platform: Platform, user: str, account: str, asset: str, margin: Decimal = Decimal(100)) -> None:
    """A long position on the asset at leverage 1, worth the margin at the price of the exchange.

    The reading of the account shows it too, with the margin the exchange declares for it (R1.6.1).
    """
    account_id = account_id_of(platform, user, account)
    tenant_id = platform.tenant_of(user)
    accounts = InMemoryAccountRepositoryAdapter(platform.accounts, tenant_id)
    access = TradingAccessFromAccounts(accounts, FakeCredentialOpenerAdapter(platform.vault)).access(account_id)
    size = margin / platform.order_exchange.markets[asset].mid_price
    platform.order_exchange.hold(access, HeldPosition(asset, Direction.LONG, size, 1))
    reading = platform.account_activity.activities.get(account_id, an_activity())
    held = (*reading.positions, a_position(asset, margin=margin, size=size))
    platform.account_activity.activities[account_id] = replace(reading, positions=held)


def open_assets(platform: Platform) -> set[str]:
    """The assets with a position open on the exchange: the scenarios of a flow have one account only, which may be
    removed by now, so the exchange is read directly."""
    return {coin for _, coin in platform.order_exchange.positions}


def stop(platform: Platform, lifecycle: Lifecycle, user: str, name: str) -> None:
    lifecycle.user = user
    command = StopFlowCommand(flow_named(platform, user, name).id, platform.user_id_of(user))

    def stop_flow() -> None:
        lifecycle.stop = platform.use_cases_of(user).stop_flow.execute(command)

    attempt(lifecycle, stop_flow)


def attempt(lifecycle: Lifecycle, action: Callable[[], object]) -> None:
    try:
        action()
    except AutotradingError as error:
        lifecycle.error = error


def modify(platform: Platform, lifecycle: Lifecycle, user: str, name: str, **changes: object) -> None:
    lifecycle.user = user
    command = ModifyFlowCommand(flow_named(platform, user, name).id, **changes)  # type: ignore[arg-type]  # each step names the part it changes
    attempt(lifecycle, lambda: platform.use_cases_of(user).modify_flow.execute(command))


@given(quoted('che "{user}" ha il flusso "{name}" sul conto "{account}" con asset "{assets}"'))
def flow_on_account(
    platform: Platform, lifecycle: Lifecycle, user: str, name: str, *, account: str, assets: str
) -> None:
    add_flow(platform, lifecycle, user, name, account=account, assets=names(assets))


@given(quoted('che il flusso "{name}" è archiviato'))
def flow_archived(platform: Platform, lifecycle: Lifecycle, name: str) -> None:
    put_in_status(platform, lifecycle.user, name, FlowStatus.ARCHIVED)


@given(quoted('che il flusso "{name}" è fermo'))
def flow_stopped(platform: Platform, lifecycle: Lifecycle, name: str) -> None:
    assert flow_named(platform, lifecycle.user, name).status is FlowStatus.STOPPED


@given(quoted('che il flusso "{name}" ha una posizione aperta su "{asset}"'))
def flow_holds_position(platform: Platform, lifecycle: Lifecycle, name: str, asset: str) -> None:
    assert asset in flow_named(platform, lifecycle.user, name).configuration.assets
    hold_position(platform, lifecycle.user, "test-1", asset)


@given(quoted('che il flusso "{name}" è nello stato "{status}"'))
def flow_brought_to_status(platform: Platform, lifecycle: Lifecycle, name: str, status: str) -> None:
    put_in_status(platform, lifecycle.user, name, FlowStatus(status))


@when(quoted('"{user}" modifica gli asset del flusso "{name}" in "{assets}"'))
def modify_assets(platform: Platform, lifecycle: Lifecycle, user: str, name: str, assets: str) -> None:
    modify(platform, lifecycle, user, name, assets=names(assets))


@when(quoted('"{user}" modifica il modello del flusso "{name}" in "{model}"'))
def modify_model(platform: Platform, lifecycle: Lifecycle, user: str, name: str, model: str) -> None:
    modify(platform, lifecycle, user, name, model=model)


@then(quoted('la modifica è rifiutata con il motivo "{reason}"'))
def modification_refused(lifecycle: Lifecycle, reason: str) -> None:
    assert str(lifecycle.error) == reason


@then(quoted('"{user}" ha il flusso "{name}"'))
def flow_present(platform: Platform, user: str, name: str) -> None:
    assert [flow.name.value for flow in platform.use_cases_of(user).list_flows.execute()].count(name) == 1


@given(quoted('che l\'exchange rifiuta la chiusura della posizione su "{asset}" con il messaggio "{message}"'))
def closing_refused(platform: Platform, asset: str, message: str) -> None:
    platform.order_exchange.closing_rejections[asset] = message


@then(quoted('sull\'exchange la posizione su "{asset}" è chiusa'))
def position_closed(platform: Platform, asset: str) -> None:
    assert asset not in open_assets(platform)


@then(quoted('il flusso "{name}" è nello stato "{status}"'))
def flow_status(platform: Platform, lifecycle: Lifecycle, name: str, status: str) -> None:
    assert flow_named(platform, lifecycle.user, name).status.value == status
