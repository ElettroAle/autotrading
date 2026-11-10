from pytest_bdd import given, scenarios, then, when

from autotrading.domain.orders.order import OrderStatus
from tests.support.steps import quoted
from tests.support.trading import Trading

scenarios("E0-esecuzione-verificata/F0.3-esecuzione-degli-ordini/R0.3.3-errori-dell-exchange.feature")

UNRECOGNIZED = "Something went wrong on our side, code 7f3a"


@given(quoted("che l'exchange rifiuta l'ordine con il messaggio \"{message}\""))
def exchange_refuses(trading: Trading, message: str) -> None:
    trading.exchange.rejection = message


@given("che l'exchange rifiuta l'ordine con un messaggio che la piattaforma non riconosce")
def exchange_refuses_unrecognized(trading: Trading) -> None:
    trading.exchange.rejection = UNRECOGNIZED


@given("che l'exchange non risponde entro 10 secondi all'invio di un ordine")
def exchange_silent(trading: Trading) -> None:
    trading.exchange.silent = True


@when(quoted('la piattaforma invia un ordine sul conto "{account}"'))
def platform_sends(trading: Trading, account: str) -> None:
    trading.open_long(account)


@then(quoted('l\'esito dell\'ordine è "{status}" con il motivo "{reason}"'))
def outcome_status_and_reason(trading: Trading, status: str, reason: str) -> None:
    assert trading.order().status == OrderStatus(status)
    assert trading.reason() == reason


@then(quoted('l\'esito riporta il messaggio originale "{message}"'))
def outcome_reports_message(trading: Trading, message: str) -> None:
    rejection = trading.order().rejection
    assert rejection is not None
    assert rejection.exchange_message == message


@then("l'esito riporta il messaggio originale dell'exchange")
def outcome_reports_unrecognized(trading: Trading) -> None:
    rejection = trading.order().rejection
    assert rejection is not None
    assert rejection.exchange_message == UNRECOGNIZED


@then("l'ordine rifiutato è registrato con il suo identificativo della piattaforma")
def rejection_recorded(trading: Trading) -> None:
    recorded = trading.orders.get(trading.last_sent().id)
    assert recorded.status is OrderStatus.REJECTED


@then("la piattaforma non ritenta l'ordine")
def no_retry(trading: Trading) -> None:
    assert len(trading.exchange.sent) == 1


@then("la piattaforma accetta le richieste successive")
def accepts_next_requests(trading: Trading) -> None:
    trading.exchange.rejection = None
    (account,) = trading.accounts
    trading.open_long(account)
    assert trading.order().status is OrderStatus.FILLED


@then("la piattaforma cerca sull'exchange l'ordine tramite il suo identificativo")
def looked_up_by_id(trading: Trading) -> None:
    assert trading.exchange.lookups == [trading.last_sent().id]


@then("l'esito dell'ordine è quello trovato sull'exchange, oppure \"esito sconosciuto\" se l'ordine non risulta")
def outcome_found_or_unknown(trading: Trading) -> None:
    found = trading.exchange.executions.get(trading.last_sent().id)
    expected = OrderStatus.UNKNOWN if found is None else OrderStatus.FILLED
    assert trading.order().status is expected


@then(quoted('l\'esito "{status}" è registrato e riportato'))
def status_recorded_and_reported(trading: Trading, status: str) -> None:
    assert trading.recorded().status == OrderStatus(status)
    assert trading.order().status == OrderStatus(status)
