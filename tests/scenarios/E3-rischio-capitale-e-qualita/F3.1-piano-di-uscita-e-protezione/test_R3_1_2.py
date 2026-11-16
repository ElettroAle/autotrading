"""R3.1.2: stop loss and take profit on the exchange for every position a flow opens, the closings they make in the
history of the flow and the defaults of the flow, run as the worker and the API compose them (ADR
ordini-di-protezione-sull-exchange, ADR stop-loss-e-take-profit-predefiniti-del-flusso, ADR
chiusure-per-protezione-nello-storico).
"""

import json
from dataclasses import replace
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.create_flow import CreateFlowCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from tests.support.activity import a_fill, a_position, an_activity
from tests.support.flow_cycles import FlowCycles, at
from tests.support.flows import OPENROUTER_MODEL
from tests.support.steps import quoted

scenarios(
    "E3-rischio-capitale-e-qualita/F3.1-piano-di-uscita-e-protezione/R3.1.2-stop-loss-e-take-profit-sull-exchange.feature"
)

# A tenth of the money of the flow at leverage 2: within the exposure of the flow and above the exchange minimum.
QUOTA = 0.1
LEVERAGE = 2
ENTRY_PRICE = Decimal(60000)
FEE = Decimal("0.02")
NUMBER = r"(?P<{}>-?\d+(?:,\d+)?)"
NO_DECISIONS = '{"decisioni": []}'
LEVELS = {"obiettivo": "target", "stop": "stop"}
KIND_OF = {"stop loss": ProtectionKind.STOP_LOSS, "take profit": ProtectionKind.TAKE_PROFIT}


def number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


class Protection:
    """The flow whose agent opens, the account on the exchange, and what the user changed or created."""

    def __init__(self, flow_cycles: FlowCycles) -> None:
        self.flow_cycles = flow_cycles
        self.error: AutotradingError | None = None
        self.versions_before = 0
        self.created: Flow | None = None

    def address(self, flow: str) -> str:
        return self.flow_cycles.credentials_of(flow).value("account_address")

    def at_price(self, asset: str, price: Decimal) -> None:
        """The market and the execution of the next orders at this price."""
        flow_cycles = self.flow_cycles
        flow_cycles.limits.set(asset, market_price=price)
        exchange = flow_cycles.platform.order_exchange
        exchange.markets[asset] = replace(exchange.markets[asset], mid_price=price)
        exchange.fill_at = (price, FEE)

    def open(self, flow: str, side: str, asset: str, plan: dict[str, object]) -> None:
        decision = {
            "asset": asset,
            "azione": "apri",
            "direzione": side,
            "quota": QUOTA,
            "leva": LEVERAGE,
            "obiettivo": None,
            "stop": None,
            "invalidazione": None,
            "confidenza": 70,
            "ragionamento": "rottura della resistenza",
        }
        self.flow_cycles.model.text = json.dumps({"decisioni": [{**decision, **plan}]})
        self.flow_cycles.run(flow)
        self.flow_cycles.model.text = NO_DECISIONS

    def protections(self, flow: str, asset: str) -> tuple[ProtectionOrder, ...]:
        return self.flow_cycles.platform.protection_exchange.of(self.address(flow), asset)

    def protection(self, flow: str, asset: str, kind: ProtectionKind) -> ProtectionOrder:
        [protection] = [each for each in self.protections(flow, asset) if each.kind is kind]
        return protection

    def notes(self, flow: str) -> list[str]:
        document = self.flow_cycles.last_record(flow).document(CycleStep.ORDER_EXECUTION)
        assert document is not None
        outcome = document["risultato"]
        assert isinstance(outcome, list)
        return [each["text"] for each in outcome if each.get("tipo") == "ProtectionNote"]

    def show_position(self, flow: str, asset: str) -> None:
        """The position the opening left, as the exchange shows it to the reconciliation."""
        recorded = self.flow_cycles.flow(flow)
        held = a_position(asset, margin=Decimal(10), size=Decimal("0.0003"), leverage=LEVERAGE)
        activity = an_activity(positions=(held,))
        self.flow_cycles.platform.activity_reader.activities[self.address(flow)] = activity
        self.flow_cycles.platform.ledger.expect(recorded.id, asset, held.size)

    def modify(self, user: str, flow: str, **changes: Decimal) -> None:
        recorded = self.flow_cycles.flow(flow)
        self.versions_before = recorded.configuration.version
        command = ModifyFlowCommand(recorded.id, **changes)  # type: ignore[arg-type]  # each step names the part it changes
        try:
            self.flow_cycles.platform.use_cases_of(user).modify_flow.execute(command)
        except AutotradingError as error:
            self.error = error

    def closed(self, flow: str, asset: str) -> list[ClosedPosition]:
        recorded = self.flow_cycles.flow(flow)
        return [
            position
            for position in self.flow_cycles.platform.closed_positions.positions
            if position.flow_id == recorded.id and position.asset == asset
        ]


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def protection(flow_cycles: FlowCycles) -> Protection:
    return Protection(flow_cycles)


def plan_of(target: str | None = None, stop: str | None = None) -> dict[str, object]:
    return {
        "obiettivo": None if target is None else int(number(target)),
        "stop": None if stop is None else int(number(stop)),
    }


# Given


@given(
    quoted(
        'che "{user}" ha il flusso "{flow}" attivo con asset "{asset}", stop loss predefinito {stop}% e nessun take '
        "profit predefinito"
    )
)
def active_flow(protection: Protection, user: str, flow: str, asset: str, stop: str) -> None:
    flow_cycles = protection.flow_cycles
    flow_cycles.add_flow(user, flow, assets=(asset,))
    flow_cycles.reconfigure(
        flow,
        lambda configuration: replace(configuration, protection_defaults=ProtectionDefaults.of(number(stop), None)),
    )
    assert flow_cycles.flow(flow).configuration.protection_defaults.take_profit_percent is None
    protection.at_price(asset, ENTRY_PRICE)


@given(quoted('che "{flow}" ha take profit predefinito {percent}%'))
def default_take_profit(protection: Protection, flow: str, percent: str) -> None:
    def changed(configuration: FlowConfiguration) -> FlowConfiguration:
        defaults = configuration.protection_defaults
        return replace(
            configuration, protection_defaults=ProtectionDefaults.of(defaults.stop_loss_percent, number(percent))
        )

    protection.flow_cycles.reconfigure(flow, changed)


@given(
    parsers.re(r"^che l'exchange rifiuta gli ordini di (?P<kind>stop loss|take profit) con \"(?P<message>[^\"]+)\"$")
)
def exchange_refuses(protection: Protection, kind: str, message: str) -> None:
    protection.flow_cycles.platform.protection_exchange.rejections[KIND_OF[kind]] = message


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha una posizione long su "(?P<asset>[^"]+)" con stop loss a '
        rf"{NUMBER.format('stop')} e take profit a {NUMBER.format('target')}$"
    )
)
def protected_position(protection: Protection, flow: str, asset: str, stop: str, target: str) -> None:
    protection.open(flow, "long", asset, plan_of(target, stop))
    protection.show_position(flow, asset)
    # A cycle reads the account with the position open: the reconciliation of the next one compares with it.
    protection.flow_cycles.run(flow, "10:15")
    assert {each.kind for each in protection.protections(flow, asset)} == set(KIND_OF.values())


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha una posizione long su "(?P<asset>[^"]+)" con prezzo d\'ingresso '
        rf"{NUMBER.format('price')} e nessun ordine di stop loss sull'exchange$"
    )
)
def unprotected_position(protection: Protection, flow: str, asset: str, price: str) -> None:
    held = HeldPosition(asset, Direction.LONG, Decimal("0.0003"), LEVERAGE, number(price))
    protection.flow_cycles.platform.order_exchange.positions[protection.address(flow), asset] = held
    protection.show_position(flow, asset)
    assert protection.protections(flow, asset) == ()


# When


@when(
    parsers.re(
        r'^"(?P<flow>[^"]+)" apre (?P<side>long|short) su "(?P<asset>[^"]+)" al prezzo d\'ingresso '
        rf"{NUMBER.format('price')} senza piano di uscita$"
    )
)
def opens_without_plan(protection: Protection, flow: str, side: str, asset: str, price: str) -> None:
    protection.at_price(asset, number(price))
    protection.open(flow, side, asset, plan_of())


@when(
    parsers.re(
        r'^"(?P<flow>[^"]+)" apre long su "(?P<asset>[^"]+)" al prezzo d\'ingresso '
        rf"{NUMBER.format('price')} con obiettivo {NUMBER.format('target')} e stop {NUMBER.format('stop')}$"
    )
)
def opens_with_plan(protection: Protection, flow: str, asset: str, price: str, target: str, stop: str) -> None:  # noqa: PLR0917 - one argument per value of the step
    protection.at_price(asset, number(price))
    protection.open(flow, "long", asset, plan_of(target, stop))


@when(
    parsers.re(
        r'^"(?P<flow>[^"]+)" apre long su "(?P<asset>[^"]+)" al prezzo d\'ingresso '
        rf"{NUMBER.format('price')} con (?P<level>obiettivo|stop) {NUMBER.format('value')}$"
    )
)
def opens_with_level(protection: Protection, flow: str, asset: str, price: str, level: str, value: str) -> None:  # noqa: PLR0917 - one argument per value of the step
    protection.at_price(asset, number(price))
    protection.open(flow, "long", asset, plan_of(**{LEVELS[level]: value}))


@when(quoted('"{flow}" apre long su "{asset}"'))
def opens(protection: Protection, flow: str, asset: str) -> None:
    protection.open(flow, "long", asset, plan_of())


@when(
    parsers.re(rf"^l'exchange esegue l'ordine di (?P<kind>stop loss|take profit) con PnL {NUMBER.format('pnl')} USDC$")
)
def exchange_executes(protection: Protection, kind: str, pnl: str) -> None:
    flow_cycles = protection.flow_cycles
    address = protection.address("alfa")
    executed = flow_cycles.platform.protection_exchange.execute(address, "BTC", KIND_OF[kind])
    del flow_cycles.platform.order_exchange.positions[address, "BTC"]
    flow_cycles.platform.activity_reader.activities[address] = an_activity()
    fill = a_fill(
        "BTC", executed.client_order_id.value, realized_pnl=number(pnl), executed_at=at("10:20"), fill_id="protection"
    )
    flow_cycles.platform.activity_reader.executions.setdefault(address, []).append(fill)
    flow_cycles.run("alfa", "10:30")


@when(quoted('l\'agente di "{flow}" decide di chiudere la posizione su "{asset}"'))
def agent_closes(protection: Protection, flow: str, asset: str) -> None:
    flow_cycles = protection.flow_cycles
    decision = {"asset": asset, "azione": "chiudi", "confidenza": 70, "ragionamento": "obiettivo raggiunto"}
    flow_cycles.model.text = json.dumps({"decisioni": [decision]})
    flow_cycles.run(flow, "10:30")


@when(quoted('"{user}" imposta lo stop loss predefinito di "{flow}" a {value}%'))
def sets_default_stop(protection: Protection, user: str, flow: str, value: str) -> None:
    protection.modify(user, flow, default_stop_loss_percent=number(value))


@when(quoted('"{user}" imposta il take profit predefinito di "{flow}" a {value}%'))
def sets_default_take_profit(protection: Protection, user: str, flow: str, value: str) -> None:
    protection.modify(user, flow, default_take_profit_percent=number(value))


@when(quoted('"{user}" crea il flusso "{flow}" senza indicare lo stop loss predefinito'))
def creates_without_stop(protection: Protection, user: str, flow: str) -> None:
    flow_cycles = protection.flow_cycles
    command = CreateFlowCommand(
        name=flow,
        account_id=flow_cycles.account_of(user),
        assets=("ETH",),
        model=OPENROUTER_MODEL,
        allocated_capital=Decimal(100),
        max_leverage=5,
        max_margin_exposure_percent=Decimal(10),
    )
    protection.created = flow_cycles.platform.use_cases_of(user).create_flow.execute(command)


@when(quoted('parte il ciclo successivo di "{flow}"'))
def next_cycle(protection: Protection, flow: str) -> None:
    protection.flow_cycles.run(flow, "10:15")


# Then


@then(
    parsers.re(
        r"^sull'exchange c'è un ordine di (?P<kind>stop loss|take profit) a "
        rf"{NUMBER.format('price')} sull'intera posizione di \"(?P<flow>[^\"]+)\" su \"(?P<asset>[^\"]+)\"$"
    )
)
def protection_on_exchange(protection: Protection, kind: str, price: str, flow: str, asset: str) -> None:
    placed = protection.protection(flow, asset, KIND_OF[kind])
    assert placed.trigger_price == number(price)
    # The protection closes the position it protects: the opposite side, on the asset the position holds.
    position = protection.flow_cycles.platform.order_exchange.positions[protection.address(flow), asset]
    assert placed.closing_direction is position.direction


@then("sull'exchange non c'è un ordine di take profit per quella posizione")
def no_take_profit(protection: Protection) -> None:
    assert [each.kind for each in protection.protections("alfa", "BTC")] == [ProtectionKind.STOP_LOSS]


@then(quoted('il ciclo di "{flow}" registra "{note}"'))
def cycle_records(protection: Protection, flow: str, note: str) -> None:
    assert note in protection.notes(flow)


@then(quoted('la posizione di "{flow}" su "{asset}" viene chiusa subito'))
def closed_at_once(protection: Protection, flow: str, asset: str) -> None:
    exchange = protection.flow_cycles.platform.order_exchange
    assert (protection.address(flow), asset) not in exchange.positions
    assert [(order.coin, order.reduce_only) for order in exchange.sent] == [(asset, False), (asset, True)]
    [closed] = protection.closed(flow, asset)
    assert closed.reason.value == "stop loss non piazzato"


@then(quoted('la posizione di "{flow}" su "{asset}" resta aperta con lo stop loss a {price}'))
def open_with_stop(protection: Protection, flow: str, asset: str, price: str) -> None:
    assert (protection.address(flow), asset) in protection.flow_cycles.platform.order_exchange.positions
    assert [(each.kind, each.trigger_price) for each in protection.protections(flow, asset)] == [
        (ProtectionKind.STOP_LOSS, number(price))
    ]


@then(
    parsers.re(
        r'^lo storico delle posizioni chiuse di "(?P<flow>[^"]+)" contiene "(?P<asset>[^"]+)" con motivo '
        rf'"(?P<reason>[^"]+)" e PnL {NUMBER.format("pnl")} USDC$'
    )
)
def closed_in_history(protection: Protection, flow: str, asset: str, reason: str, pnl: str) -> None:
    [closed] = protection.closed(flow, asset)
    assert (closed.reason.value, closed.pnl, closed.side) == (reason, number(pnl), TradeSide.LONG)


@then(quoted('sull\'exchange non resta alcun ordine di protezione di "{flow}" su "{asset}"'))
def no_protection_left(protection: Protection, flow: str, asset: str) -> None:
    assert protection.protections(flow, asset) == ()
    recorded = protection.flow_cycles.flow(flow)
    assert not [
        each
        for _, each in protection.flow_cycles.platform.protections.protections
        if each.account_id == recorded.assigned_account_id and each.asset == asset
    ]


@then(quoted('la modifica viene rifiutata con "{message}"'))
def refused(protection: Protection, message: str) -> None:
    assert protection.error is not None
    assert str(protection.error) == message
    assert protection.flow_cycles.flow("alfa").configuration.version == protection.versions_before


@then(quoted('il flusso "{flow}" ha stop loss predefinito {percent}%'))
def created_with_default(protection: Protection, flow: str, percent: str) -> None:
    created = protection.created
    assert created is not None
    assert created.name.value == flow
    assert created.configuration.protection_defaults == ProtectionDefaults(number(percent), None)


@then(quoted('"{flow}" ha una nuova versione della configurazione con stop loss predefinito {percent}%'))
def new_version(protection: Protection, flow: str, percent: str) -> None:
    configuration = protection.flow_cycles.flow(flow).configuration
    assert configuration.version == protection.versions_before + 1
    assert configuration.protection_defaults.stop_loss_percent == number(percent)
