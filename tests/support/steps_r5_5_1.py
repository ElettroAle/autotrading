"""R5.5.1: the stop loss of the open positions of a flow follows the price between the cycles, by the distance, the
activation and the breakeven of the flow, with the largest profit each position reached shown to the user and, with the
option on, to the agent; run as the worker, the API and the MCP server compose them (ADR
impostazioni-dello-stop-che-segue-il-prezzo, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue, ADR
massimo-profitto-raggiunto-nello-stato-della-posizione).
"""

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.flows.create_flow import CreateFlowCommand, TrailingStopRequest
from autotrading.application.flows.follow_trailing_stops import FollowTrailingStopsCommand
from autotrading.application.flows.get_flow import GetFlowCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.application.flows.read_flow_results import ReadFlowResultsCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.flows.trailing_stop import TrailingStop
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from tests.fakes.protection_exchange import Resting
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter
from tests.support.activity import a_fill, an_activity
from tests.support.flow_cycles import FlowCycles, at
from tests.support.flows import OPENROUTER_MODEL
from tests.support.mcp_session import McpSession, body_of
from tests.support.steps_r3_1_2 import Protection, plan_of
from tests.support.steps_r5_5_3 import StopInForce

NUMBER = r"(?P<{}>\d+(?:,\d+)?)"
ENTRY = "60000"
DEFAULT_STOP = "5"
NO_DECISIONS = '{"decisioni": []}'
SETTING_OF = {"l'attivazione dello stop che segue": "activation_percent", "il pareggio": "breakeven_percent"}


NUMERIC = frozenset({"price", "high", "low", "stop", "value", "distance", "activation", "breakeven", "size", "profit"})


def numbered(text: str) -> parsers.StepParser:
    """The text of a step with its placeholders: a number where the name is of a number, a quoted text elsewhere."""
    pieces = re.split(r"\{(\w+)\}", text)
    pattern = "".join(
        (NUMBER.format(piece) if piece in NUMERIC else f'(?P<{piece}>[^"]+)') if index % 2 else re.escape(piece)
        for index, piece in enumerate(pieces)
    )
    return parsers.re(f"^{pattern}$")


def number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def _quarters() -> Iterator[str]:
    """The instants of the cycles after the opening at 10:00, one per interval of the flow."""
    minutes = 615
    while True:
        yield f"{minutes // 60}:{minutes % 60:02d}"
        minutes += 15


@dataclass
class TrailingStops:
    """The flows whose stop follows the price, the prices of the market as the worker reads them, and what the user
    changed and read."""

    stops: StopInForce
    cycles: Iterator[str] = field(default_factory=_quarters)
    error: AutotradingError | None = None
    version_before: int = 0
    created: Flow | None = None
    read_profits: dict[str, str | None] = field(default_factory=dict)
    read_flow: dict[str, object] = field(default_factory=dict)
    openings_before_check: int = 0

    @property
    def flow_cycles(self) -> FlowCycles:
        return self.stops.flow_cycles

    @property
    def protection(self) -> Protection:
        return self.stops.protection

    def ensure_flow(self, user: str, flow: str, asset: str = "BTC") -> None:
        """The flow the scenarios of the tools and of the dashboard name: active on the asset, stop loss 5%."""
        if flow not in self.flow_cycles.users:
            self.add_flow(user, flow, asset, DEFAULT_STOP)

    def add_flow(self, user: str, flow: str, asset: str, stop: str) -> None:
        self.flow_cycles.add_flow(user, flow, assets=(asset,))
        self.flow_cycles.reconfigure(
            flow,
            lambda configuration: replace(configuration, protection_defaults=ProtectionDefaults.of(number(stop), None)),
        )
        self.protection.at_price(asset, number(ENTRY))

    def follow(self, flow: str, trailing: TrailingStop) -> None:
        """The settings of the stop that follows the price as the flow holds them now, without a new version."""
        self.flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, trailing_stop=trailing))

    def trailing_of(self, flow: str) -> TrailingStop:
        return self.flow_cycles.flow(flow).configuration.trailing_stop

    def open(self, flow: str, side: str, asset: str, price: str) -> None:
        self.protection.at_price(asset, number(price))
        self.protection.open(flow, side, asset, plan_of())
        held = self.flow_cycles.platform.order_exchange.positions[self.protection.address(flow), asset]
        self.stops.show(flow, _position_of(held))
        # A cycle reads the account with the position open: the reconciliation of the next one compares with it.
        self.next_cycle(flow)

    def resize(self, flow: str, asset: str, size: Decimal) -> None:
        exchange, address = self.flow_cycles.platform.order_exchange, self.protection.address(flow)
        held = replace(exchange.positions[address, asset], size=size)
        exchange.positions[address, asset] = held
        self.stops.show(flow, replace(self._shown(flow, asset), size=size))

    def check_at(self, flow: str, asset: str, price: str) -> None:
        """The market moves to the price, and the worker checks it at its next minute."""
        self.protection.at_price(asset, number(price))
        if (self.protection.address(flow), asset) in self.flow_cycles.platform.order_exchange.positions:
            self.stops.show(flow, replace(self._shown(flow, asset), mark_price=number(price)))
        self.check(flow)

    def check(self, flow: str) -> None:
        tenant_id = self.flow_cycles.flow(flow).tenant_id
        self.openings_before_check = len(self.flow_cycles.platform.openings.openings)
        self.flow_cycles.trailing_stops_of(tenant_id).execute(FollowTrailingStopsCommand())

    def _shown(self, flow: str, asset: str) -> AccountPosition:
        activity = self.flow_cycles.platform.activity_reader.activities[self.protection.address(flow)]
        [position] = [position for position in activity.positions if position.asset == asset]
        return position

    def stops_on_exchange(self, flow: str, asset: str) -> list[Decimal]:
        return [
            order.trigger_price
            for order in self.protection.protections(flow, asset)
            if order.kind is ProtectionKind.STOP_LOSS
        ]

    def agent_updates(self, flow: str, asset: str, stop: str) -> None:
        decision = {
            "asset": asset,
            "azione": "aggiorna",
            "direzione": None,
            "quota": None,
            "leva": None,
            "obiettivo": None,
            "stop": int(number(stop)),
            "invalidazione": None,
            "togli_obiettivo": False,
            "confidenza": 70,
            "ragionamento": "proteggo il guadagno",
        }
        self.flow_cycles.model.text = json.dumps({"decisioni": [decision]})
        self.next_cycle(flow)
        self.flow_cycles.model.text = NO_DECISIONS

    def next_cycle(self, flow: str) -> None:
        self.flow_cycles.run(flow, next(self.cycles))

    def notes(self, flow: str) -> list[str]:
        """What the last cycle of the flow recorded of its risk check and of its orders."""
        record = self.flow_cycles.last_record(flow)
        documents = [record.document(step) for step in (CycleStep.RISK_CHECK, CycleStep.ORDER_EXECUTION)]
        return [text for document in documents if document is not None for text in _texts(document)]

    def modify(self, user: str, flow: str, request: TrailingStopRequest) -> None:
        recorded = self.flow_cycles.flow(flow)
        self.version_before = recorded.configuration.version
        try:
            self.flow_cycles.platform.use_cases_of(user).modify_flow.execute(
                ModifyFlowCommand(recorded.id, trailing_stop=request)
            )
        except AutotradingError as error:
            self.error = error
            return
        # The change holds from the next check of the worker, a minute later at most.
        self.check(flow)

    def read_state(self, user: str, flow: str) -> None:
        command = ReadFlowResultsCommand(self.flow_cycles.flow(flow).id.value)
        state = self.flow_cycles.platform.use_cases_of(user).read_flow_results.execute(command).state
        self.read_profits = {
            position.asset: _text_of(state.max_profit_of(position.asset)) for position in state.positions
        }

    def mcp(self) -> McpSession:
        return McpSession(self.flow_cycles.platform)


def _texts(document: object) -> Iterator[str]:
    if isinstance(document, str):
        yield document
    elif isinstance(document, dict):
        for value in document.values():
            yield from _texts(value)
    elif isinstance(document, list):
        for value in document:
            yield from _texts(value)


def _text_of(amount: Decimal | None) -> str | None:
    return None if amount is None else str(amount)


def _position_of(held: HeldPosition) -> AccountPosition:
    side = TradeSide(held.direction.value)
    return AccountPosition(
        held.coin, side, held.size, Decimal(10), Decimal(0), held.leverage, held.entry_price, held.entry_price
    )


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def trailing(flow_cycles: FlowCycles) -> TrailingStops:
    return TrailingStops(StopInForce(Protection(flow_cycles)))


# Given


@given(
    numbered(
        'che "{user}" ha il flusso "{flow}" attivo con asset "{asset}", stop loss predefinito {stop}% e distanza dello '
        "stop che segue {distance}%"
    )
)
def following_flow(trailing: TrailingStops, user: str, flow: str, asset: str, stop: str, distance: str) -> None:  # noqa: PLR0917 - one argument per value of the step
    trailing.add_flow(user, flow, asset, stop)
    trailing.follow(flow, TrailingStop(number(distance)))


@given(numbered('che "{user}" ha il flusso "{flow}" attivo con asset "{asset}" e stop loss predefinito {stop}%'))
def active_flow(trailing: TrailingStops, user: str, flow: str, asset: str, stop: str) -> None:
    trailing.add_flow(user, flow, asset, stop)


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha una posizione long su "(?P<asset>[^"]+)" con prezzo d\'ingresso '
        rf"{NUMBER.format('price')} e stop loss a {NUMBER.format('stop')}$"
    )
)
def long_position(trailing: TrailingStops, flow: str, asset: str, price: str, stop: str) -> None:
    trailing.open(flow, "long", asset, price)
    assert trailing.stops_on_exchange(flow, asset) == [number(stop)]


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha invece una posizione short su "(?P<asset>[^"]+)" con prezzo d\'ingresso '
        rf"{NUMBER.format('price')} e stop loss a {NUMBER.format('stop')}$"
    )
)
def short_position_instead(trailing: TrailingStops, flow: str, asset: str, price: str, stop: str) -> None:
    """The long of the background turned into a short at the same entry, with its stop on the exchange and recorded."""
    platform, address = trailing.flow_cycles.platform, trailing.protection.address(flow)
    long = platform.order_exchange.positions[address, asset]
    short = replace(long, direction=Direction.SHORT, entry_price=number(price))
    platform.order_exchange.positions[address, asset] = short
    [resting] = platform.protection_exchange.resting[address, asset]
    order = ProtectionOrder(asset, ProtectionKind.STOP_LOSS, Direction.SHORT, number(stop))
    platform.protection_exchange.resting[address, asset] = [Resting(resting.order_id, order)]
    recorded = trailing.flow_cycles.flow(flow)
    protections = InMemoryProtectionRepositoryAdapter(platform.protections, recorded.tenant_id)
    [placed] = protections.placed(recorded.assigned_account_id, asset)
    protections.remove(recorded.assigned_account_id, asset)
    protections.add(replace(placed, trigger_price=number(stop), client_order_id=order.client_order_id))
    trailing.stops.show(flow, _position_of(short))


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha una posizione long su "(?P<asset>[^"]+)" di dimensione '
        rf"{NUMBER.format('size')} con prezzo d'ingresso {NUMBER.format('price')}$"
    )
)
def long_position_of_size(trailing: TrailingStops, flow: str, asset: str, size: str, price: str) -> None:
    trailing.open(flow, "long", asset, price)
    trailing.resize(flow, asset, number(size))


@given(numbered('che la posizione di "{flow}" su "{asset}" ha dimensione {size}'))
def position_of_size(trailing: TrailingStops, flow: str, asset: str, size: str) -> None:
    trailing.resize(flow, asset, number(size))


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha una posizione long su "(?P<asset>[^"]+)" con massimo profitto raggiunto '
        rf"{NUMBER.format('profit')} USDC$"
    )
)
def position_with_max_profit(trailing: TrailingStops, flow: str, asset: str, profit: str) -> None:
    """Only a watched position has a largest profit: the flow follows the price at 2%, and the price went up from
    60000 by the profit on a size of 0,01."""
    trailing.ensure_flow("anna", flow, asset)
    trailing.follow(flow, TrailingStop(Decimal(2)))
    trailing.open(flow, "long", asset, ENTRY)
    size = Decimal("0.01")
    trailing.resize(flow, asset, size)
    trailing.check_at(flow, asset, str(number(ENTRY) + number(profit) / size))


@given(numbered('che "{flow}" ha attivazione dello stop che segue {activation}%'))
def with_activation(trailing: TrailingStops, flow: str, activation: str) -> None:
    trailing.follow(flow, replace(trailing.trailing_of(flow), activation_percent=number(activation)))


@given(numbered('che "{flow}" non ha distanza dello stop che segue e ha pareggio {breakeven}%'))
def breakeven_alone(trailing: TrailingStops, flow: str, breakeven: str) -> None:
    trailing.follow(flow, TrailingStop(breakeven_percent=number(breakeven)))


@given(numbered('che "{flow}" ha distanza dello stop che segue {distance}% e pareggio {breakeven}%'))
def distance_and_breakeven(trailing: TrailingStops, flow: str, distance: str, breakeven: str) -> None:
    trailing.follow(flow, TrailingStop(number(distance), breakeven_percent=number(breakeven)))


@given(numbered('che "{flow}" ha distanza dello stop che segue {distance}%'))
def with_distance(trailing: TrailingStops, flow: str, distance: str) -> None:
    trailing.follow(flow, TrailingStop(number(distance)))


@given(numbered('che "{flow}" non ha distanza dello stop che segue né pareggio'))
def without_settings(trailing: TrailingStops, flow: str) -> None:
    trailing.follow(flow, TrailingStop())


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha il massimo profitto raggiunto nel contesto dell\'agente (?P<option>acceso|spento)$'
    )
)
def max_profit_option(trailing: TrailingStops, flow: str, option: str) -> None:
    trailing.follow(flow, replace(trailing.trailing_of(flow), max_profit_in_context=option == "acceso"))


@given(numbered('che il flusso "{flow}" esisteva prima dello stop che segue il prezzo'))
def flow_from_before(trailing: TrailingStops, flow: str) -> None:
    # A version saved before reads the stop that follows the price as off (ADR impostazioni-dello-stop-che-segue-il-
    # prezzo): the flow holds the settings of then.
    trailing.follow(flow, TrailingStop())
    trailing.version_before = trailing.flow_cycles.flow(flow).configuration.version


@given(numbered('che il prezzo di "{asset}" è salito a {price}'))
@when(numbered('il prezzo di "{asset}" sale a {price}'))
@when(numbered('il prezzo di "{asset}" scende a {price}'))
@when(numbered('la piattaforma controlla il prezzo di "{asset}" a {price}'))
def price_moves(trailing: TrailingStops, asset: str, price: str) -> None:
    trailing.check_at("alfa", asset, price)


@given(numbered('che il prezzo di "{asset}" è salito a {high} e poi sceso a {low}'))
def price_up_and_down(trailing: TrailingStops, asset: str, high: str, low: str) -> None:
    trailing.check_at("alfa", asset, high)
    trailing.check_at("alfa", asset, low)


@given(numbered('che il prezzo di "{asset}" è {price}'))
def price_now(trailing: TrailingStops, asset: str, price: str) -> None:
    trailing.check_at("alfa", asset, price)


@given(
    numbered('che "{flow}" non aveva distanza dello stop che segue quando il prezzo di "{asset}" è salito a {price}')
)
def risen_without_distance(trailing: TrailingStops, flow: str, asset: str, price: str) -> None:
    trailing.follow(flow, TrailingStop())
    trailing.check_at(flow, asset, price)


@given(numbered('che l\'agente di "{flow}" ha aggiornato lo stop su "{asset}" a {stop}'))
@when(numbered('l\'agente di "{flow}" decide di aggiornare lo stop su "{asset}" a {stop}'))
def agent_updates_stop(trailing: TrailingStops, flow: str, asset: str, stop: str) -> None:
    trailing.agent_updates(flow, asset, stop)


@given(parsers.re(r"^che l'exchange rifiuta gli ordini di stop loss con \"(?P<message>[^\"]+)\"$"))
def exchange_refuses_stops(trailing: TrailingStops, message: str) -> None:
    trailing.flow_cycles.platform.protection_exchange.rejections[ProtectionKind.STOP_LOSS] = message


# When


@when(numbered('parte il ciclo successivo di "{flow}"'))
def next_cycle(trailing: TrailingStops, flow: str) -> None:
    trailing.next_cycle(flow)


@when(parsers.re(rf"^l'exchange esegue l'ordine di stop loss a {NUMBER.format('stop')}$"))
def exchange_executes_stop(trailing: TrailingStops, stop: str) -> None:
    flow_cycles, address = trailing.flow_cycles, trailing.protection.address("alfa")
    platform = flow_cycles.platform
    held = platform.order_exchange.positions.pop((address, "BTC"))
    executed = platform.protection_exchange.execute(address, "BTC", ProtectionKind.STOP_LOSS)
    assert executed.trigger_price == number(stop)
    platform.activity_reader.activities[address] = an_activity()
    pnl = (executed.trigger_price - held.entry_price) * held.size
    fill = a_fill("BTC", executed.client_order_id.value, realized_pnl=pnl, executed_at=at("10:05"), fill_id="stop")
    platform.activity_reader.executions.setdefault(address, []).append(fill)
    trailing.next_cycle("alfa")


@when(
    numbered(
        '"{user}" crea il flusso "{flow}" senza indicare distanza, attivazione, pareggio e opzione del massimo profitto'
    )
)
def creates_without_settings(trailing: TrailingStops, user: str, flow: str) -> None:
    flow_cycles = trailing.flow_cycles
    command = CreateFlowCommand(
        name=flow,
        account_id=flow_cycles.account_of(user),
        assets=("ETH",),
        model=OPENROUTER_MODEL,
        allocated_capital=Decimal(100),
        max_leverage=5,
        max_margin_exposure_percent=Decimal(10),
    )
    trailing.created = flow_cycles.platform.use_cases_of(user).create_flow.execute(command)


@when(numbered('"{user}" legge la configurazione di "{flow}"'))
def reads_configuration(trailing: TrailingStops, user: str, flow: str) -> None:
    command = GetFlowCommand(trailing.flow_cycles.flow(flow).id)
    trailing.created = trailing.flow_cycles.platform.use_cases_of(user).get_flow.execute(command)


@when(numbered('"{user}" imposta la distanza dello stop che segue di "{flow}" a {value}%'))
def sets_distance(trailing: TrailingStops, user: str, flow: str, value: str) -> None:
    trailing.modify(user, flow, TrailingStopRequest(distance_percent=number(value)))


@when(numbered('"{user}" imposta l\'attivazione dello stop che segue di "{flow}" a {value}% senza distanza'))
def sets_activation_alone(trailing: TrailingStops, user: str, flow: str, value: str) -> None:
    trailing.modify(user, flow, TrailingStopRequest(activation_percent=number(value)))


@when(
    parsers.re(
        r'^"(?P<user>[^"]+)" imposta (?P<setting>l\'attivazione dello stop che segue|il pareggio) di "(?P<flow>[^"]+)" '
        rf"a {NUMBER.format('value')}%$"
    )
)
def sets_percent(trailing: TrailingStops, user: str, setting: str, flow: str, value: str) -> None:
    request = TrailingStopRequest(**{SETTING_OF[setting]: number(value)})  # type: ignore[arg-type]  # one part by name
    trailing.modify(user, flow, request)


@when(numbered('"{user}" toglie la distanza dello stop che segue di "{flow}"'))
def removes_distance(trailing: TrailingStops, user: str, flow: str) -> None:
    trailing.modify(user, flow, TrailingStopRequest(remove_distance=True))


@when(numbered('"{user}" legge lo stato di "{flow}"'))
def reads_state(trailing: TrailingStops, user: str, flow: str) -> None:
    trailing.read_state(user, flow)


@when(numbered('il client MCP di "{user}" imposta la distanza dello stop che segue di "{flow}" a {value}%'))
def mcp_sets_distance(trailing: TrailingStops, user: str, flow: str, value: str) -> None:
    trailing.ensure_flow(user, flow)
    recorded = trailing.flow_cycles.flow(flow)
    trailing.version_before = recorded.configuration.version
    modification = {"trailing_stop": {"distance_percent": str(number(value))}}
    arguments = {"flow_id": str(recorded.id.value), "modification": modification}
    result = trailing.mcp().call_as(user, "modify_flow", arguments)
    assert not result.is_error, body_of(result)
    flow_view = body_of(trailing.mcp().call_as(user, "get_flow", {"flow_id": str(recorded.id.value)}))
    trailing.read_flow = flow_view


@when(numbered('il client MCP di "{user}" legge lo stato di "{flow}"'))
def mcp_reads_state(trailing: TrailingStops, user: str, flow: str) -> None:
    flow_id = str(trailing.flow_cycles.flow(flow).id.value)
    body = body_of(trailing.mcp().call_as(user, "read_flow_state", {"flow_id": flow_id}))
    trailing.read_profits = {position["asset"]: position["max_profit_reached"] for position in body["positions"]}


# Then


@then(
    parsers.re(
        r"^sull'exchange l'unico ordine di stop loss di \"(?P<flow>[^\"]+)\" su \"(?P<asset>[^\"]+)\" è a "
        rf"{NUMBER.format('stop')}$"
    )
)
def only_stop_on_exchange(trailing: TrailingStops, flow: str, asset: str, stop: str) -> None:
    assert trailing.stops_on_exchange(flow, asset) == [number(stop)]


@then(numbered('il ciclo di "{flow}" registra "{note}"'))
def cycle_records(trailing: TrailingStops, flow: str, note: str) -> None:
    assert note in trailing.notes(flow)


@then(numbered('il ciclo successivo di "{flow}" registra "{note}"'))
def next_cycle_records(trailing: TrailingStops, flow: str, note: str) -> None:
    trailing.next_cycle(flow)
    assert note in trailing.notes(flow)
    # Recorded once: the cycle after says nothing more of it.
    trailing.next_cycle(flow)
    assert note not in trailing.notes(flow)


@then(
    parsers.re(
        r'^lo stato del flusso inviato all\'agente riporta per la posizione su "(?P<asset>[^"]+)" stop '
        rf"{NUMBER.format('stop')}$"
    )
)
def stop_in_context(trailing: TrailingStops, asset: str, stop: str) -> None:
    held = trailing.stops.held_in_context(asset)
    assert isinstance(held["stop"], str)
    assert number(held["stop"]) == number(stop)


@then(
    parsers.re(
        r"^lo stato del flusso inviato all\'agente (?P<outcome>riporta|non riporta) per la posizione su "
        rf'"(?P<asset>[^"]+)" il massimo profitto raggiunto {NUMBER.format("profit")} USDC$'
    )
)
def max_profit_in_context(trailing: TrailingStops, outcome: str, asset: str, profit: str) -> None:
    held = trailing.stops.held_in_context(asset)
    if outcome == "non riporta":
        assert "massimo_profitto_raggiunto" not in held
        return
    reached = held["massimo_profitto_raggiunto"]
    assert isinstance(reached, str)
    assert number(reached) == number(profit)


@then(numbered('lo storico delle posizioni chiuse di "{flow}" contiene "{asset}" con motivo "{reason}"'))
def closed_in_history(trailing: TrailingStops, flow: str, asset: str, reason: str) -> None:
    [closed] = trailing.protection.closed(flow, asset)
    assert closed.reason.value == reason


@then(numbered('la piattaforma non sorveglia il prezzo di "{asset}" per "{flow}" tra un ciclo e l\'altro'))
def not_watched(trailing: TrailingStops, asset: str, flow: str) -> None:
    platform, recorded = trailing.flow_cycles.platform, trailing.flow_cycles.flow(flow)
    assert platform.watched_positions.of(recorded.tenant_id, recorded.id) == ()
    # The check opened no account: no price of the flow was read.
    assert len(platform.openings.openings) == trailing.openings_before_check
    assert trailing.stops_on_exchange(flow, asset) == [Decimal(57000)]


@then(numbered('il flusso "{flow}" non ha distanza dello stop che segue, attivazione né pareggio'))
@then(numbered('"{flow}" non ha distanza dello stop che segue, attivazione né pareggio'))
def no_settings(trailing: TrailingStops, flow: str) -> None:
    assert trailing.created is not None
    assert trailing.created.name.value == flow
    trailing_stop = trailing.created.configuration.trailing_stop
    assert (trailing_stop.distance_percent, trailing_stop.activation_percent, trailing_stop.breakeven_percent) == (
        None,
        None,
        None,
    )


@then(numbered('il flusso "{flow}" ha il massimo profitto raggiunto nel contesto dell\'agente spento'))
def option_off(trailing: TrailingStops, flow: str) -> None:
    assert trailing.created is not None
    assert trailing.created.name.value == flow
    assert trailing.created.configuration.trailing_stop.max_profit_in_context is False


@then(numbered('la configurazione di "{flow}" resta alla stessa versione'))
def same_version(trailing: TrailingStops, flow: str) -> None:
    assert trailing.flow_cycles.flow(flow).configuration.version == trailing.version_before


@then(numbered('la modifica viene rifiutata con "{message}"'))
def refused(trailing: TrailingStops, message: str) -> None:
    assert trailing.error is not None
    assert str(trailing.error) == message
    assert trailing.flow_cycles.flow("alfa").configuration.version == trailing.version_before


@then(numbered('"{flow}" ha una nuova versione della configurazione con distanza dello stop che segue {distance}%'))
def new_version_with_distance(trailing: TrailingStops, flow: str, distance: str) -> None:
    configuration = trailing.flow_cycles.flow(flow).configuration
    assert configuration.version == trailing.version_before + 1
    assert configuration.trailing_stop.distance_percent == number(distance)


@then(numbered('"{flow}" ha una nuova versione della configurazione senza distanza dello stop che segue'))
def new_version_without_distance(trailing: TrailingStops, flow: str) -> None:
    configuration = trailing.flow_cycles.flow(flow).configuration
    assert configuration.version == trailing.version_before + 1
    assert configuration.trailing_stop.distance_percent is None


@then(numbered('la posizione su "{asset}" riporta massimo profitto raggiunto {profit} USDC'))
def max_profit_read(trailing: TrailingStops, asset: str, profit: str) -> None:
    read = trailing.read_profits[asset]
    assert read is not None
    assert number(read) == number(profit)


@then(numbered('la posizione su "{asset}" non riporta nessun massimo profitto raggiunto'))
def no_max_profit_read(trailing: TrailingStops, asset: str) -> None:
    assert asset in trailing.read_profits
    assert trailing.read_profits[asset] is None


@then(numbered('il dettaglio di "{flow}" letto dagli strumenti riporta distanza dello stop che segue {distance}%'))
def tools_detail(trailing: TrailingStops, flow: str, distance: str) -> None:
    assert trailing.read_flow["name"] == flow
    trailing_stop = trailing.read_flow["trailing_stop"]
    assert isinstance(trailing_stop, dict)
    assert number(trailing_stop["distance_percent"]) == number(distance)
