"""R3.2.3: the emergency closing of a flow, of an account or of every flow, on the use cases of the API with the fake
adapters (ADR chiusura-di-emergenza-per-ambito). playwright-bdd runs the confirmation of the dashboard on its build
(ADR chiusura-di-emergenza-nella-dashboard); here the same scenario proves that the API gives the confirmation what it
shows and closes nothing while the user chooses. The page puts the command alone at the bottom of the page (ADR
zona-di-emergenza-in-fondo-alla-pagina), which playwright-bdd proves; here the scenarios of the zone prove what the zone
shows comes from the API: one scope per command, the positions it counts, and nothing closed by opening the page.
"""

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.close_in_emergency import CloseInEmergencyCommand
from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.list_closed_positions import ListClosedPositionsCommand
from autotrading.application.flows.preview_emergency_closing import PreviewEmergencyClosingCommand
from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.emergency_closing import EmergencyClosing, EmergencyScope, FlowEmergencyOutcome
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.order import Order
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.trading_access import TradingAccess
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter
from tests.support.flow_closing_steps import *  # noqa: F403 - the steps of the closings that reach the ledger late
from tests.support.flow_closings import FlowClosings
from tests.support.flows import a_configuration, a_flow, account_id_of
from tests.support.lifecycle_steps import hold_position
from tests.support.orders import a_flow_order
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios(
    "E3-rischio-capitale-e-qualita/F3.2-limiti-di-rischio/R3.2.3-chiusura-di-emergenza/api/R3.2.3-chiusura-di-emergenza.feature"
)

STOP_PRICE = Decimal(95000)
EMERGENCY_COMMAND = "Chiusura di emergenza"
# The emergency closing of a flow sits with Archivia at the bottom of the settings of the flow (Bug 560).
FLOW_ZONE = "Zona pericolosa"
LAUNCHED_AT = datetime(2026, 11, 12, 10, 30, tzinfo=UTC)


@dataclass
class Emergency:
    platform: Platform
    user: str = ""
    # The account of every flow of the scenario, by the name of the flow.
    accounts: dict[str, str] = field(default_factory=dict)
    owners: dict[str, str] = field(default_factory=dict)
    assets: dict[str, str] = field(default_factory=dict)
    closing: EmergencyClosing | None = None
    error: AutotradingError | None = None
    confirmation: str = ""
    orders_before: int = 0
    # The commands of the zone of the page opened, each with the positions the API counts for its scope.
    zone: dict[str, int] = field(default_factory=dict)

    def flow(self, name: str) -> Flow:
        owner = self.owners[name]
        (flow,) = [flow for flow in self.platform.flows.of(self.platform.tenant_of(owner)) if flow.name.value == name]
        return flow

    def access(self, user: str, account: str) -> TradingAccess:
        accounts = InMemoryAccountRepositoryAdapter(self.platform.accounts, self.platform.tenant_of(user))
        opener = FakeCredentialOpenerAdapter(self.platform.vault)
        account_id = self.platform.account_named(user, account).id.value
        return OpenTradingAccessUseCase(accounts, opener).execute(OpenTradingAccessCommand(account_id))

    def is_open(self, user: str, account: str, asset: str) -> bool:
        address = self.access(user, account).value("account_address")
        return (address, asset) in self.platform.order_exchange.positions

    def flow_position_open(self, name: str) -> bool:
        return self.is_open(self.owners[name], self.accounts[name], self.assets[name])

    def add_flow(self, user: str, account: str, name: str, asset: str, *, held: bool = True) -> Flow:
        account_id = account_id_of(self.platform, user, account)
        configuration = a_configuration(assets=(asset,))
        flow = a_flow(
            self.platform.tenant_of(user),
            name=name,
            status=FlowStatus.ACTIVE,
            account_id=account_id,
            configuration=configuration,
        )
        self.platform.flows.flows.append(flow)
        self.platform.flows.save_version(flow)
        self.owners[name], self.accounts[name], self.assets[name] = user, account, asset
        if held:
            hold_position(self.platform, user, account, asset)
            self.platform.orders_of(flow.tenant_id).add(_opening_order(account_id, flow, asset))
        return flow

    def previewed(self, user: str, scope: EmergencyScope) -> int:
        command = PreviewEmergencyClosingCommand(scope)
        return self.platform.use_cases_of(user).preview_emergency_closing.execute(command).positions

    def open_page(self, user: str, zone: dict[str, EmergencyScope]) -> None:
        self.user = user
        self.orders_before = len(self.platform.order_exchange.sent)
        self.zone = {command: self.previewed(user, scope) for command, scope in zone.items()}

    def nothing_run(self) -> bool:
        statuses = {flow.status for flow in self.platform.flows.flows}
        return len(self.platform.order_exchange.sent) == self.orders_before and statuses == {FlowStatus.ACTIVE}

    def launch(self, user: str, scope: EmergencyScope) -> None:
        self.user = user
        command = CloseInEmergencyCommand(scope, self.platform.user_id_of(user))
        try:
            self.closing = self.platform.use_cases_of(user).close_in_emergency.execute(command)
        except AutotradingError as error:
            self.error = error

    def outcome_of(self, name: str) -> FlowEmergencyOutcome:
        assert self.closing is not None, self.error
        (outcome,) = [each for each in self.closing.outcomes if each.flow_name == name]
        return outcome


def _positions_text(positions: int) -> str:
    return "1 posizione" if positions == 1 else f"{positions} posizioni"


def _opening_order(account_id: UUID, flow: Flow, asset: str) -> Order:
    order = a_flow_order(account_id, flow.id.value)
    market_order = replace(order.request.market_order, coin=asset)
    return replace(order, request=replace(order.request, market_order=market_order))


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    for asset, price in (("SOL", Decimal(200)), ("DOGE", Decimal("0.4"))):
        platform.order_exchange.markets[asset] = Market(
            asset, max_leverage=10, size_decimals=1, mid_price=price, min_order_value=Decimal(10)
        )
    return platform


@pytest.fixture
def flow_closings(platform: Platform) -> FlowClosings:
    return FlowClosings(platform)


@pytest.fixture
def emergency(platform: Platform) -> Emergency:
    return Emergency(platform)


@given(
    quoted(
        'che "{user}" ha sul conto "{account}" i flussi attivi "{first}" con una posizione su "{first_asset}" e '
        '"{second}" con una posizione su "{second_asset}"'
    )
)
def two_active_flows(  # noqa: PLR0917 - one argument per value of the step
    emergency: Emergency, user: str, account: str, first: str, first_asset: str, second: str, second_asset: str
) -> None:
    emergency.add_flow(user, account, first, first_asset)
    emergency.add_flow(user, account, second, second_asset)


@given(quoted('che "{user}" ha sul conto "{account}" il flusso attivo "{name}" con una posizione su "{asset}"'))
def one_active_flow(emergency: Emergency, user: str, account: str, name: str, asset: str) -> None:
    emergency.add_flow(user, account, name, asset)


@given(quoted('che "{user}" ha sul conto "{account}" anche il flusso attivo "{name}" senza posizioni'))
def flow_without_positions(emergency: Emergency, user: str, account: str, name: str) -> None:
    # On another account than the flow that trades it, the asset is free for this flow (R1.1.2).
    emergency.add_flow(user, account, name, "ETH", held=False)


@given(quoted('che "{user}" ha sul conto "{account}" anche il flusso {status} "{name}"'))
def flow_without_market(emergency: Emergency, user: str, account: str, status: str, name: str) -> None:
    flow = emergency.add_flow(user, account, name, "ETH", held=False)
    flows = emergency.platform.flows.flows
    flows[flows.index(flow)] = replace(flow, status=FlowStatus(status))


@given("che sono le 10:30 UTC del 12 novembre 2026")
def at_half_past_ten(platform: Platform) -> None:
    platform.now = LAUNCHED_AT


@given(quoted('che la posizione di "{name}" su "{asset}" ha un ordine di stop loss sull\'exchange'))
def stop_loss_on_exchange(emergency: Emergency, platform: Platform, name: str, asset: str) -> None:
    flow, owner = emergency.flow(name), emergency.owners[name]
    order = ProtectionOrder(asset, ProtectionKind.STOP_LOSS, Direction.LONG, STOP_PRICE)
    order_id = platform.protection_exchange.place(emergency.access(owner, emergency.accounts[name]), order)
    protection = PlacedProtection(
        flow.assigned_account_id, flow.id.value, asset, order.kind, STOP_PRICE, order_id, order.client_order_id
    )
    InMemoryProtectionRepositoryAdapter(platform.protections, flow.tenant_id).add(protection)


@given(quoted('che sul conto "{account}" c\'è una posizione su "{asset}" che nessun flusso possiede'))
def position_of_no_flow(emergency: Emergency, platform: Platform, account: str, asset: str) -> None:
    owner = emergency.owners[next(name for name, each in emergency.accounts.items() if each == account)]
    hold_position(platform, owner, account, asset)


@given(quoted('che l\'exchange rifiuta la chiusura su "{asset}" con "{message}"'))
def closing_refused(platform: Platform, asset: str, message: str) -> None:
    platform.order_exchange.closing_rejections[asset] = message


@given(quoted('che il flusso "{name}" è in pausa con la posizione su "{asset}" aperta'))
def flow_paused(emergency: Emergency, platform: Platform, name: str, asset: str) -> None:
    flow = emergency.flow(name)
    platform.flows.flows = [
        replace(each, status=FlowStatus.PAUSED) if each.id == flow.id else each for each in platform.flows.flows
    ]
    assert emergency.is_open(emergency.owners[name], emergency.accounts[name], asset)


@given(quoted('che "{user}" ha il flusso "{name}" con una posizione aperta'))
def flow_of_another_tenant(emergency: Emergency, user: str, name: str) -> None:
    emergency.add_flow(user, "test-1", name, "BTC")


@when(quoted('"{user}" lancia la chiusura di emergenza del flusso "{name}"'))
def launch_on_flow(emergency: Emergency, user: str, name: str) -> None:
    emergency.launch(user, EmergencyScope(flow_id=emergency.flow(name).id))


@when(quoted('"{user}" lancia la chiusura di emergenza del conto "{account}"'))
def launch_on_account(emergency: Emergency, platform: Platform, user: str, account: str) -> None:
    emergency.launch(user, EmergencyScope(account_id=platform.account_named(user, account).id.value))


@when(quoted('"{user}" lancia la chiusura di emergenza di tutti i suoi flussi'))
def launch_on_all(emergency: Emergency, user: str) -> None:
    emergency.launch(user, EmergencyScope())


@when(quoted('"{user}" sceglie nella dashboard la chiusura di emergenza del conto "{account}"'))
def choose_on_account(emergency: Emergency, platform: Platform, user: str, account: str) -> None:
    emergency.user = user
    emergency.orders_before = len(platform.order_exchange.sent)
    scope = EmergencyScope(account_id=platform.account_named(user, account).id.value)
    preview = platform.use_cases_of(user).preview_emergency_closing.execute(PreviewEmergencyClosingCommand(scope))
    emergency.confirmation = (
        f"Chiudere {preview.positions} posizioni dei flussi del conto {account} e metterli in pausa?"
    )


@when(quoted('"{user}" apre nella dashboard le impostazioni del flusso "{name}"'))
def open_flow_settings(emergency: Emergency, user: str, name: str) -> None:
    flow = emergency.flow(name)
    emergency.open_page(user, {f"{EMERGENCY_COMMAND} del flusso {name}": EmergencyScope(flow_id=flow.id)})


@when(quoted('"{user}" apre nella dashboard la pagina dei conti'))
def open_accounts_page(emergency: Emergency, user: str) -> None:
    accounts = emergency.platform.use_cases_of(user).list_accounts.execute()
    emergency.open_page(
        user,
        {
            f"{EMERGENCY_COMMAND} del conto {account.name.value}": EmergencyScope(account_id=account.id.value)
            for account in accounts
        },
    )


@when(quoted('"{user}" apre nella dashboard le impostazioni generali'))
def open_general_settings(emergency: Emergency, user: str) -> None:
    emergency.open_page(user, {f"{EMERGENCY_COMMAND} di tutti i flussi": EmergencyScope()})


@when(quoted('"{user}" sceglie la chiusura di emergenza del flusso "{name}" nel riquadro "{zone}"'))
def choose_flow_in_zone(emergency: Emergency, user: str, name: str, zone: str) -> None:
    assert zone == FLOW_ZONE
    open_flow_settings(emergency, user, name)
    positions = emergency.zone[f"{EMERGENCY_COMMAND} del flusso {name}"]
    emergency.confirmation = f"Chiudere {_positions_text(positions)} del flusso {name} e metterlo in pausa?"


@then(quoted('la posizione di "{name}" su "{asset}" è chiusa'))
def position_closed(emergency: Emergency, name: str, asset: str) -> None:
    assert emergency.closing is not None, emergency.error
    assert asset in emergency.outcome_of(name).closed
    assert not emergency.is_open(emergency.owners[name], emergency.accounts[name], asset)


@then(quoted('il flusso "{name}" è in pausa con motivo "{reason}"'))
def paused_with_reason(emergency: Emergency, platform: Platform, name: str, reason: str) -> None:
    flow = emergency.flow(name)
    assert flow.status is FlowStatus.PAUSED
    assert platform.flows.pause_reasons.get(flow.id) == reason


@then(quoted('i flussi "{first}" e "{second}" restano attivi con le loro posizioni'))
def others_active(emergency: Emergency, first: str, second: str) -> None:
    for name in (first, second):
        assert emergency.flow(name).status is FlowStatus.ACTIVE
        assert emergency.flow_position_open(name)


@then(quoted('le posizioni di "{first}" e "{second}" sono chiuse'))
def two_closed(emergency: Emergency, first: str, second: str) -> None:
    for name in (first, second):
        assert emergency.outcome_of(name).closed == (emergency.assets[name],)
        assert not emergency.flow_position_open(name)


@then(quoted('i flussi "{first}" e "{second}" sono in pausa con motivo "{reason}"'))
def two_paused(emergency: Emergency, platform: Platform, first: str, second: str, reason: str) -> None:
    for name in (first, second):
        paused_with_reason(emergency, platform, name, reason)


@then(quoted('il flusso "{name}" resta attivo con la sua posizione'))
def still_active(emergency: Emergency, name: str) -> None:
    assert emergency.flow(name).status is FlowStatus.ACTIVE
    assert emergency.flow_position_open(name)


@then(quoted('le posizioni di "{first}", "{second}" e "{third}" sono chiuse'))
def three_closed(emergency: Emergency, first: str, second: str, third: str) -> None:
    for name in (first, second, third):
        assert emergency.outcome_of(name).closed == (emergency.assets[name],)
        assert not emergency.flow_position_open(name)


@then(quoted('i flussi "{first}", "{second}" e "{third}" sono in pausa con motivo "{reason}"'))
def three_paused(  # noqa: PLR0917 - one argument per value of the step
    emergency: Emergency, platform: Platform, first: str, second: str, third: str, reason: str
) -> None:
    for name in (first, second, third):
        paused_with_reason(emergency, platform, name, reason)


@then(quoted('sull\'exchange non resta alcun ordine di protezione di "{name}" su "{asset}"'))
def no_protection_left(emergency: Emergency, platform: Platform, name: str, asset: str) -> None:
    address = emergency.access(emergency.owners[name], emergency.accounts[name]).value("account_address")
    assert platform.protection_exchange.cancelled
    assert platform.protection_exchange.resting.get((address, asset), []) == []


@then(quoted('lo storico delle posizioni chiuse di "{name}" contiene "{asset}" con motivo "{reason}"'))
def history_reason(emergency: Emergency, platform: Platform, name: str, asset: str, reason: str) -> None:
    command = ListClosedPositionsCommand(emergency.flow(name).id.value)
    positions = platform.use_cases_of(emergency.owners[name]).list_closed_positions.execute(command).positions
    assert [(position.asset, position.reason.value) for position in positions] == [(asset, reason)]


@then(quoted('la posizione su "{asset}" resta aperta'))
def position_of_no_flow_open(emergency: Emergency, asset: str) -> None:
    assert emergency.closing is not None, emergency.error
    assert emergency.is_open(emergency.user, "test-1", asset)
    assert all(asset not in outcome.closed for outcome in emergency.closing.outcomes)


@then(quoted('l\'esito riporta per "{name}" la posizione "{asset}" non chiusa con "{reason}"'))
def left_open(emergency: Emergency, name: str, asset: str, reason: str) -> None:
    left = emergency.outcome_of(name).left_open
    assert [(position.asset, position.reason) for position in left] == [(asset, reason)]


@then(quoted('il flusso "{name}" resta in pausa'))
def still_paused(emergency: Emergency, platform: Platform, name: str) -> None:
    flow = emergency.flow(name)
    assert flow.status is FlowStatus.PAUSED
    # Paused by the user before: the pause keeps its own reason, none.
    assert platform.flows.pause_reasons.get(flow.id) is None


@then(quoted('l\'esito riporta "{remark}"'))
def remark(emergency: Emergency, remark: str) -> None:
    assert emergency.closing is not None, emergency.error
    (outcome,) = emergency.closing.outcomes
    assert outcome.remark == remark


@then(quoted('la dashboard chiede conferma con "{text}"'))
def confirmation_asked(emergency: Emergency, text: str) -> None:
    assert emergency.confirmation == text


@then(quoted('nessuna posizione viene chiusa finché "{user}" non conferma'))
def nothing_closed(emergency: Emergency, platform: Platform, user: str) -> None:
    assert user == emergency.user
    assert len(platform.order_exchange.sent) == emergency.orders_before
    assert emergency.flow_position_open("alfa")
    assert emergency.flow_position_open("beta")


@then(quoted('la chiusura di emergenza del flusso "{name}" sta nel riquadro "{zone}" in fondo alla pagina'))
def flow_closing_in_zone(emergency: Emergency, name: str, zone: str) -> None:
    assert zone == FLOW_ZONE
    assert emergency.zone == {f"{EMERGENCY_COMMAND} del flusso {name}": 1}


@then(quoted('la chiusura di emergenza di tutti i flussi sta nel riquadro "{zone}" in fondo alla pagina'))
def all_closing_in_zone(emergency: Emergency, zone: str) -> None:
    assert zone == "Zona di emergenza"
    assert emergency.zone == {f"{EMERGENCY_COMMAND} di tutti i flussi": len(emergency.owners)}


@then(
    quoted(
        'il riquadro "{zone}" in fondo alla pagina contiene la chiusura di emergenza dei conti "{first}" e "{second}"'
    )
)
def accounts_closing_in_zone(emergency: Emergency, zone: str, first: str, second: str) -> None:
    assert zone == "Zona di emergenza"
    # alfa and beta on the first account, gamma on the second (background).
    assert emergency.zone == {f"{EMERGENCY_COMMAND} del conto {first}": 2, f"{EMERGENCY_COMMAND} del conto {second}": 1}


@then(quoted('il riquadro "{zone}" non contiene altri comandi'))
def zone_alone(emergency: Emergency, zone: str) -> None:
    assert zone == "Zona di emergenza"
    assert [command for command in emergency.zone if not command.startswith(EMERGENCY_COMMAND)] == []
    assert len(emergency.zone) == 1


@then(quoted('la pagina del flusso "{name}" non contiene la chiusura di emergenza'))
def flow_page_without_emergency(emergency: Emergency, name: str) -> None:
    # The commands of the flow are those its status admits; the emergency closing is none of them.
    status = emergency.flow(name).status
    assert [action for action in FlowAction if status in action.starts_from] == [FlowAction.PAUSE, FlowAction.STOP]
    assert emergency.nothing_run()


@then("l'elenco dei flussi non contiene la chiusura di emergenza")
def flows_list_without_emergency(emergency: Emergency) -> None:
    # The list of the flows reads only the flows: no closing and no count of the positions to close starts from it.
    assert emergency.nothing_run()
    assert all(emergency.flow_position_open(name) for name in emergency.owners)


@then("i comandi dei conti non contengono la chiusura di emergenza")
def account_commands_without_emergency(emergency: Emergency) -> None:
    # Opening the page runs no closing: only the command of the zone does, once confirmed.
    assert emergency.nothing_run()
    assert all(emergency.flow_position_open(name) for name in emergency.owners)


@then(quoted('il flusso "{name}" resta {status}'))
def status_kept(emergency: Emergency, name: str, status: str) -> None:
    assert emergency.flow(name).status == FlowStatus(status)


@then(quoted('l\'esito non riporta il flusso "{name}"'))
def not_in_outcome(emergency: Emergency, name: str) -> None:
    assert emergency.closing is not None, emergency.error
    assert name not in [outcome.flow_name for outcome in emergency.closing.outcomes]


@then(
    quoted('la chiusura di emergenza è registrata alle 10:30 UTC del 12 novembre 2026 con ambito il conto "{account}"')
)
def closing_recorded(emergency: Emergency, platform: Platform, account: str) -> None:
    [recorded] = platform.emergency_closings
    assert recorded.closed_at == LAUNCHED_AT
    assert recorded.scope == EmergencyScope(account_id=platform.account_named(emergency.user, account).id.value)


@then(
    quoted(
        'la chiusura registrata riporta chiuse le posizioni di "{first}" su "{first_asset}" '
        'e di "{second}" su "{second_asset}"'
    )
)
def recorded_outcome(platform: Platform, first: str, first_asset: str, second: str, second_asset: str) -> None:
    [recorded] = platform.emergency_closings
    closed = {outcome.flow_name: outcome.closed for outcome in recorded.outcomes}
    assert closed == {first: (first_asset,), second: (second_asset,)}


@then("il comando viene rifiutato come flusso inesistente")
def refused_as_missing(emergency: Emergency) -> None:
    assert emergency.closing is None
    assert isinstance(emergency.error, FlowNotFoundError)


@then(quoted('la posizione di "{name}" resta aperta'))
def flow_position_still_open(emergency: Emergency, name: str) -> None:
    assert emergency.flow_position_open(name)
