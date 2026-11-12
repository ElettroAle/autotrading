from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersCommand, ExecuteFlowOrdersUseCase
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, FlowOrder
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.order import Order, OrderOrigin, OrderStatus
from tests.support.steps import quoted
from tests.support.trading import HYPERLIQUID, Trading

scenarios("E1-flussi-autonomi/F1.5-rischio-ed-esecuzione/R1.5.5-esecuzione-delle-decisioni.feature")

OPENING_VALUE = Decimal(100)
OPENING_LEVERAGE = 2


class FlowExecution:
    """The flow, its account on the exchange, the orders the risk check approved and the cycles that run them."""

    def __init__(self) -> None:
        self.trading = Trading()
        self.flows: dict[str, UUID] = {}
        self.cycles: dict[str, datetime] = {}
        self.account = ""
        self.approved: list[FlowOrder] = []

    def flow(self, name: str, account: str) -> None:
        self.flows[name] = uuid4()
        self.account = account
        self.trading.add_account(account)

    def cycle(self, name: str) -> datetime:
        return self.cycles.setdefault(name, datetime(2026, 11, 12, 10, 15 * len(self.cycles), tzinfo=UTC))

    def execute(self, flow: str, cycle: str) -> None:
        trading = self.trading
        use_case = ExecuteFlowOrdersUseCase(
            trading.accesses, {HYPERLIQUID: trading.exchange}, trading.orders, trading.slippage
        )
        command = ExecuteFlowOrdersCommand(
            trading.accounts[self.account], self.flows[flow], self.cycle(cycle), tuple(self.approved)
        )
        use_case.execute(command)

    def recorded(self, asset: str) -> Order:
        (order,) = [order for order in self.trading.orders.orders if order.request.market_order.coin == asset]
        return order

    def sent_index(self, asset: str, *, closing: bool) -> int:
        sent = self.trading.exchange.sent
        return next(index for index, order in enumerate(sent) if order.coin == asset and order.reduce_only == closing)


@pytest.fixture
def execution() -> FlowExecution:
    return FlowExecution()


def opening(asset: str) -> FlowOpening:
    return FlowOpening(asset, Direction.LONG, OPENING_VALUE, OPENING_LEVERAGE)


@given(quoted('che "anna" ha il flusso "{flow}" sul conto "{account}" con una posizione long aperta su "{asset}"'))
def flow_with_position(execution: FlowExecution, flow: str, account: str, asset: str) -> None:
    execution.flow(flow, account)
    access = execution.trading.access_of(account)
    execution.trading.exchange.hold(access, HeldPosition(asset, Direction.LONG, Decimal("0.5"), 3))


@given(quoted('che il rischio approva la chiusura su "{closed}" e un\'apertura long su "{opened}"'))
def close_and_open(execution: FlowExecution, closed: str, opened: str) -> None:
    # The risk check gives them in the order of the decisions: the opening first, so only the rule puts it second.
    execution.approved = [opening(opened), FlowClosing(closed)]


@given(quoted('che il rischio approva un\'apertura long su "{asset}" al prezzo atteso di {price}'))
def open_at_expected_price(execution: FlowExecution, asset: str, price: str) -> None:
    market = execution.trading.exchange.markets[asset]
    assert market.mid_price == Decimal(price)
    execution.approved = [opening(asset)]


@given(quoted('che il rischio approva un\'apertura long su "{asset}"'))
def open_long(execution: FlowExecution, asset: str) -> None:
    execution.approved = [opening(asset)]


@given(
    parsers.re(
        r'^che l\'exchange ammette per "(?P<asset>\w+)" un valore minimo di ordine di (?P<minimum>\d+) USDC'
        r" al prezzo di (?P<price>\d+) con (?P<decimals>\d+) decimali di quantità$"
    )
)
def exchange_market(execution: FlowExecution, asset: str, minimum: str, price: str, decimals: str) -> None:
    current = execution.trading.exchange.markets[asset]
    execution.trading.exchange.markets[asset] = Market(
        asset, current.max_leverage, int(decimals), Decimal(price), Decimal(minimum)
    )


@given(quoted('che il rischio approva un\'apertura long su "{asset}" di valore {value} USDC'))
def open_with_value(execution: FlowExecution, asset: str, value: str) -> None:
    execution.approved = [FlowOpening(asset, Direction.LONG, Decimal(value), 1)]


@given(parsers.re(r"^che l\'exchange esegue l\'ordine a (?P<price>\d+) con commissione (?P<fee>\d+,\d+) USDC$"))
def exchange_fills_at(execution: FlowExecution, price: str, fee: str) -> None:
    execution.trading.exchange.fill_at = (Decimal(price), Decimal(fee.replace(",", ".")))


@given(quoted('che l\'exchange rifiuta la chiusura su "{asset}" con il messaggio "{message}"'))
def exchange_refuses_closing(execution: FlowExecution, asset: str, message: str) -> None:
    # The fake refuses every closing: the scenario has a single one, on the position the flow holds.
    assert asset in {coin for _, coin in execution.trading.exchange.positions}
    execution.trading.exchange.closing_rejection = message


@when(quoted('il flusso "{flow}" esegue gli ordini del ciclo "{cycle}"'))
def execute_orders(execution: FlowExecution, flow: str, cycle: str) -> None:
    execution.execute(flow, cycle)


@then(quoted('l\'ordine di chiusura su "{closed}" è inviato prima dell\'ordine di apertura su "{opened}"'))
def closing_sent_first(execution: FlowExecution, closed: str, opened: str) -> None:
    assert execution.sent_index(closed, closing=True) < execution.sent_index(opened, closing=False)


@then(quoted("l'ordine su \"{asset}\" porta l'identificativo della piattaforma"))
def order_carries_platform_id(execution: FlowExecution, asset: str) -> None:
    recorded = execution.recorded(asset)
    assert isinstance(recorded.id, ClientOrderId)
    assert execution.trading.exchange.sent[execution.sent_index(asset, closing=False)].id == recorded.id


@then(
    quoted('l\'ordine su "{asset}" è collegato al flusso "{flow}", al ciclo "{cycle}" e alla decisione su "{decision}"')
)
def order_linked(execution: FlowExecution, asset: str, flow: str, cycle: str, decision: str) -> None:
    source = execution.recorded(asset).request.source
    assert source.origin is OrderOrigin.FLOW
    assert source.flow == FlowLink(execution.flows[flow], execution.cycles[cycle], decision)


@then(
    parsers.re(
        r'^il ciclo registra per "(?P<asset>\w+)" il prezzo eseguito (?P<price>\d+)'
        r" e la commissione (?P<fee>\d+,\d+) USDC$"
    )
)
def real_outcome_recorded(execution: FlowExecution, asset: str, price: str, fee: str) -> None:
    executed = execution.recorded(asset).execution
    assert executed is not None
    assert (executed.average_price, executed.fee) == (Decimal(price), Decimal(fee.replace(",", ".")))


@then(quoted('il ciclo registra per "{asset}" l\'ordine rifiutato con il messaggio "{message}"'))
def rejection_recorded(execution: FlowExecution, asset: str, message: str) -> None:
    recorded = execution.recorded(asset)
    assert recorded.status is OrderStatus.REJECTED
    assert recorded.rejection is not None
    assert recorded.rejection.exchange_message == message


@then(quoted('l\'ordine di apertura su "{asset}" è inviato'))
def opening_sent(execution: FlowExecution, asset: str) -> None:
    assert execution.sent_index(asset, closing=False) >= 0
    assert execution.recorded(asset).status is OrderStatus.FILLED


@then(parsers.re(r'^l\'ordine su "(?P<asset>\w+)" è inviato con quantità (?P<size>\d+,\d+)$'))
def sent_with_size(execution: FlowExecution, asset: str, size: str) -> None:
    sent = execution.trading.exchange.sent[execution.sent_index(asset, closing=False)]
    assert sent.size == Decimal(size.replace(",", "."))
