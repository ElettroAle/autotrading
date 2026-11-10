from decimal import Decimal

from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.order import OrderOrigin, OrderSource, OrderStatus
from tests.support.steps import quoted
from tests.support.trading import Trading

scenarios("E0-esecuzione-verificata/F0.3-esecuzione-degli-ordini/R0.3.4-esito-reale-registrato.feature")


def executed_on_exchange(trading: Trading) -> Execution:
    return trading.exchange.executions[trading.last_sent().id]


def recorded_execution(trading: Trading) -> Execution:
    execution = trading.recorded().execution
    assert execution is not None, "the order was recorded without an execution"
    return execution


@given(parsers.parse("che l'exchange esegue solo il {percent:d}% della dimensione richiesta"))
def partial_fill(trading: Trading, percent: int) -> None:
    trading.exchange.fill_ratio = Decimal(percent) / 100


@when(quoted('la piattaforma invia sul conto "{account}" un ordine di apertura che l\'exchange esegue'))
def platform_sends_executed(trading: Trading, account: str) -> None:
    trading.open_long(account)


@when(quoted('la piattaforma invia sul conto "{account}" un ordine di apertura'))
def platform_sends_opening(trading: Trading, account: str) -> None:
    trading.open_long(account)


@when(quoted('la procedura di verifica invia un ordine sul conto "{account}"'))
def verification_sends(trading: Trading, account: str) -> None:
    trading.open_long(account, source=OrderSource(OrderOrigin.VERIFICATION))


@then("l'ordine è registrato con la dimensione eseguita letta dall'exchange")
def recorded_filled_size(trading: Trading) -> None:
    assert recorded_execution(trading).filled_size == executed_on_exchange(trading).filled_size


@then("l'ordine è registrato con il prezzo medio di esecuzione letto dall'exchange")
def recorded_average_price(trading: Trading) -> None:
    assert recorded_execution(trading).average_price == executed_on_exchange(trading).average_price


@then("l'ordine è registrato con la commissione letta dall'exchange")
def recorded_fee(trading: Trading) -> None:
    assert recorded_execution(trading).fee == executed_on_exchange(trading).fee


@then("l'ordine è registrato con l'istante di esecuzione letto dall'exchange")
def recorded_executed_at(trading: Trading) -> None:
    assert recorded_execution(trading).executed_at == executed_on_exchange(trading).executed_at


@then(quoted('l\'ordine è registrato come "{status}"'))
def recorded_status(trading: Trading, status: str) -> None:
    assert trading.recorded().status == OrderStatus(status)


@then("l'ordine è registrato con la dimensione richiesta e la dimensione eseguita")
def recorded_requested_and_filled(trading: Trading) -> None:
    assert trading.recorded().request.market_order.size == trading.last_sent().size
    assert recorded_execution(trading).filled_size == trading.last_sent().size * trading.exchange.fill_ratio


@then(quoted("l'ordine è registrato con l'origine \"{origin}\""))
def recorded_origin(trading: Trading, origin: str) -> None:
    assert trading.recorded().request.source.origin == OrderOrigin(origin)
