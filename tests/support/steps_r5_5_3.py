"""R5.5.3: the state of an open position shows the stop loss and the take profit the platform keeps waiting on the
exchange, whatever their origin, to the agent, in the API and in the MCP tools, run as the worker, the API and the MCP
server compose them (ADR stop-e-obiettivo-in-vigore-nello-stato-della-posizione).
"""

from dataclasses import dataclass, field, replace
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.flows.read_flow_results import ReadFlowResultsCommand
from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from tests.fakes.protection_exchange import Resting
from tests.support.activity import an_activity
from tests.support.flow_cycles import FlowCycles
from tests.support.mcp_session import McpSession, body_of
from tests.support.steps import quoted
from tests.support.steps_r3_1_2 import Protection, plan_of

NUMBER = r"(?P<{}>\d+(?:,\d+)?)"
SIZE = Decimal("0.0003")
LEVERAGE = 2
NEXT_CYCLE = "10:15"
# The identifier the exchange gave the stop loss placed before the platform recorded its protections.
EARLIER_STOP_ID = "earlier-stop"


def number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


@dataclass
class StopInForce:
    """The flow whose positions are open on the exchange, and the stop of each position as the user read it."""

    protection: Protection
    read_stops: dict[str, str | None] = field(default_factory=dict)

    @property
    def flow_cycles(self) -> FlowCycles:
        return self.protection.flow_cycles

    def show(self, flow: str, position: AccountPosition) -> None:
        """The position as the exchange shows it to the worker, by address, and to the API, by account."""
        flow_cycles, recorded = self.flow_cycles, self.flow_cycles.flow(flow)
        activity: AccountActivity = an_activity(positions=(position,))
        flow_cycles.platform.activity_reader.activities[self.protection.address(flow)] = activity
        flow_cycles.platform.account_activity.activities[recorded.assigned_account_id] = activity
        signed = position.size if position.side is TradeSide.LONG else -position.size
        flow_cycles.platform.ledger.expect(recorded.id, position.asset, signed)

    def open_long(self, flow: str, asset: str, price: str, stop: str | None = None) -> None:
        self.protection.at_price(asset, number(price))
        self.protection.open(flow, "long", asset, plan_of(stop=stop))
        held = self.flow_cycles.platform.order_exchange.positions[self.protection.address(flow), asset]
        self.show(flow, _position_of(held))

    def stop_on_exchange(self, flow: str, asset: str) -> Decimal:
        return self.protection.protection(flow, asset, ProtectionKind.STOP_LOSS).trigger_price

    def held_in_context(self, asset: str) -> dict[str, object]:
        state = self.flow_cycles.context()["stato_del_flusso"]
        assert isinstance(state, dict)
        [held] = [held for held in state["posizioni_aperte"] if held["asset"] == asset]
        assert isinstance(held, dict)
        return held


def _position_of(held: HeldPosition) -> AccountPosition:
    side = TradeSide(held.direction.value)
    return AccountPosition(
        held.coin, side, held.size, Decimal(10), Decimal(0), held.leverage, held.entry_price, held.entry_price
    )


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def stops(flow_cycles: FlowCycles) -> StopInForce:
    return StopInForce(Protection(flow_cycles))


def _active_flow(stops: StopInForce, user: str, flow: str, asset: str, stop: str) -> None:
    flow_cycles = stops.flow_cycles
    flow_cycles.add_flow(user, flow, assets=(asset,))
    flow_cycles.reconfigure(
        flow,
        lambda configuration: replace(configuration, protection_defaults=ProtectionDefaults.of(number(stop), None)),
    )


# Given


@given(
    quoted(
        'che "{user}" ha il flusso "{flow}" attivo con asset "{asset}", stop loss predefinito {stop}% e nessun take '
        "profit predefinito"
    )
)
def active_flow_without_take_profit(stops: StopInForce, user: str, flow: str, asset: str, stop: str) -> None:
    _active_flow(stops, user, flow, asset, stop)
    assert stops.flow_cycles.flow(flow).configuration.protection_defaults.take_profit_percent is None


@given(quoted('che "{user}" ha il flusso "{flow}" attivo con asset "{asset}" e stop loss predefinito {stop}%'))
def active_flow(stops: StopInForce, user: str, flow: str, asset: str, stop: str) -> None:
    _active_flow(stops, user, flow, asset, stop)


@given(quoted('che "{flow}" ha take profit predefinito {percent}%'))
def default_take_profit(stops: StopInForce, flow: str, percent: str) -> None:
    def with_take_profit(defaults: ProtectionDefaults) -> ProtectionDefaults:
        return ProtectionDefaults.of(defaults.stop_loss_percent, number(percent))

    stops.flow_cycles.reconfigure(
        flow,
        lambda configuration: replace(
            configuration, protection_defaults=with_take_profit(configuration.protection_defaults)
        ),
    )


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha aperto long su "(?P<asset>[^"]+)" al prezzo d\'ingresso '
        rf"{NUMBER.format('price')} senza piano di uscita$"
    )
)
def opened_without_plan(stops: StopInForce, flow: str, asset: str, price: str) -> None:
    stops.open_long(flow, asset, price)


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha aperto long su "(?P<asset>[^"]+)" al prezzo d\'ingresso '
        rf"{NUMBER.format('price')} con stop {NUMBER.format('stop')}, riportato a {NUMBER.format('reported')}$"
    )
)
def opened_with_stop_reported(  # noqa: PLR0917 - one argument per value of the step
    stops: StopInForce, flow: str, asset: str, price: str, stop: str, reported: str
) -> None:
    stops.open_long(flow, asset, price, stop)
    assert stops.stop_on_exchange(flow, asset) == number(reported)


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" aveva già una posizione short su "(?P<asset>[^"]+)" con prezzo d\'ingresso '
        rf"{NUMBER.format('price')} e l'ordine di stop loss a {NUMBER.format('stop')} sull'exchange$"
    )
)
def earlier_short_with_stop(stops: StopInForce, flow: str, asset: str, price: str, stop: str) -> None:
    platform, address = stops.flow_cycles.platform, stops.protection.address(flow)
    stops.protection.at_price(asset, number(price))
    held = HeldPosition(asset, Direction.SHORT, SIZE, LEVERAGE, number(price))
    platform.order_exchange.positions[address, asset] = held
    # Placed before the platform recorded the protections it placed: the exchange has it, the platform does not.
    order = ProtectionOrder(asset, ProtectionKind.STOP_LOSS, Direction.SHORT, number(stop))
    platform.protection_exchange.resting[address, asset] = [Resting(EARLIER_STOP_ID, order)]
    stops.show(flow, _position_of(held))
    assert platform.protections.protections == []


# When


@when(quoted('parte il ciclo successivo di "{flow}"'))
def next_cycle(stops: StopInForce, flow: str) -> None:
    stops.flow_cycles.run(flow, NEXT_CYCLE)


@when(quoted('"{user}" legge lo stato di "{flow}"'))
def user_reads_the_state(stops: StopInForce, user: str, flow: str) -> None:
    command = ReadFlowResultsCommand(stops.flow_cycles.flow(flow).id.value)
    state = stops.flow_cycles.platform.use_cases_of(user).read_flow_results.execute(command).state
    stops.read_stops = {
        position.asset: _text_of(state.exit_plan_of(position.asset).stop) for position in state.positions
    }


@when(quoted('il client MCP di "{user}" legge lo stato di "{flow}"'))
def mcp_client_reads_the_state(stops: StopInForce, user: str, flow: str) -> None:
    flow_id = str(stops.flow_cycles.flow(flow).id.value)
    session = McpSession(stops.flow_cycles.platform)
    body = body_of(session.call_as(user, "read_flow_state", {"flow_id": flow_id}))
    stops.read_stops = {position["asset"]: position["stop_price"] for position in body["positions"]}


def _text_of(price: Decimal | None) -> str | None:
    return None if price is None else str(price)


# Then


@then(
    parsers.re(
        r'^lo stato del flusso inviato all\'agente riporta per la posizione su "(?P<asset>[^"]+)" stop '
        rf"{NUMBER.format('stop')}$"
    )
)
def stop_in_context(stops: StopInForce, asset: str, stop: str) -> None:
    held = stops.held_in_context(asset)
    assert isinstance(held["stop"], str)
    assert number(held["stop"]) == number(stop)


@then(
    parsers.re(
        r'^lo stato del flusso inviato all\'agente riporta per la posizione su "(?P<asset>[^"]+)" stop '
        rf"{NUMBER.format('stop')} e obiettivo {NUMBER.format('target')}$"
    )
)
def stop_and_target_in_context(stops: StopInForce, asset: str, stop: str, target: str) -> None:
    held = stops.held_in_context(asset)
    assert isinstance(held["stop"], str)
    assert isinstance(held["obiettivo"], str)
    assert (number(held["stop"]), number(held["obiettivo"])) == (number(stop), number(target))


@then(quoted('lo stato del flusso inviato all\'agente riporta per la posizione su "{asset}" nessun obiettivo'))
def no_target_in_context(stops: StopInForce, asset: str) -> None:
    assert stops.held_in_context(asset)["obiettivo"] is None


@then(quoted('la posizione su "{asset}" riporta stop {stop}'))
def stop_read(stops: StopInForce, asset: str, stop: str) -> None:
    read = stops.read_stops[asset]
    assert read is not None
    assert number(read) == number(stop)
