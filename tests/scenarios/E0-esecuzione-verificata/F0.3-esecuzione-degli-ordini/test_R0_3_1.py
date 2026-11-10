from decimal import Decimal

from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.orders.open_position import OpenPositionCommand
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.order import OrderStatus
from autotrading.domain.orders.slippage import Slippage
from tests.support.steps import quoted
from tests.support.trading import VERIFICATION, Trading

scenarios("E0-esecuzione-verificata/F0.3-esecuzione-degli-ordini/R0.3.1-apertura-di-una-posizione.feature")


@given(
    quoted(
        'che il conto "{account}" è su "{exchange}" con margine disponibile {margin} USDC e nessuna posizione aperta'
    )
)
def account_with_margin(trading: Trading, account: str, exchange: str) -> None:
    trading.add_account(account, exchange)


@given("che lo scostamento massimo di prezzo non è configurato")
def slippage_not_configured(trading: Trading) -> None:
    trading.slippage = Slippage.default()


@given(parsers.parse("che lo scostamento massimo di prezzo è configurato all'{percent:d}%"))
def slippage_configured(trading: Trading, percent: int) -> None:
    trading.slippage = Slippage.percent(Decimal(percent))


@given(quoted("che il prezzo di \"{coin}\" si muove di più dell'{percent}% prima dell'esecuzione"))
def price_moves(trading: Trading, coin: str, percent: str) -> None:
    trading.exchange.price_moves[coin] = Decimal(percent) / 100 + Decimal("0.001")


@given(quoted('che l\'exchange ammette per "{coin}" una leva massima di {maximum}'))
def maximum_leverage(trading: Trading, coin: str, maximum: str) -> None:
    market = trading.exchange.markets[coin]
    trading.exchange.markets[coin] = type(market)(coin, int(maximum), market.size_decimals, market.mid_price)


@given(quoted('che l\'exchange ammette per "{coin}" dimensioni multiple di {step}'))
def size_step(trading: Trading, coin: str, step: str) -> None:
    market = trading.exchange.markets[coin]
    decimals = -int(Decimal(step).as_tuple().exponent)
    trading.exchange.markets[coin] = type(market)(coin, market.max_leverage, decimals, market.mid_price)


@when(
    quoted(
        'la piattaforma apre sul conto "{account}" una posizione "{direction}" su "{coin}" '
        "con leva {leverage} e valore {value} USDC"
    )
)
def platform_opens(trading: Trading, account: str, *, direction: str, coin: str, leverage: str, value: str) -> None:
    command = OpenPositionCommand(
        trading.accounts[account], coin, Direction(direction), int(leverage), Decimal(value), VERIFICATION
    )
    trading.open_position(command)


@when(
    quoted(
        'la piattaforma apre sul conto "{account}" una posizione "{direction}" su "{coin}" '
        "con un valore che corrisponde a {size} BTC"
    )
)
def platform_opens_size(trading: Trading, account: str, direction: str, coin: str, size: str) -> None:
    value = Decimal(size) * trading.exchange.markets[coin].mid_price
    trading.open_position(
        OpenPositionCommand(trading.accounts[account], coin, Direction(direction), 2, value, VERIFICATION)
    )


@then(quoted('sull\'exchange il conto "{account}" ha una posizione "{direction}" su "{coin}"'))
def exchange_has_position(trading: Trading, account: str, direction: str, coin: str) -> None:
    position = trading.exchange.position(trading.access_of(account), coin)
    assert position is not None
    assert position.direction == Direction(direction)


@then(quoted('la posizione su "{coin}" ha leva {leverage}'))
def position_has_leverage(trading: Trading, coin: str, leverage: str) -> None:
    (position,) = [position for (_, held), position in trading.exchange.positions.items() if held == coin]
    assert position.leverage == int(leverage)


@then("l'ordine inviato porta un identificativo della piattaforma")
def sent_order_carries_platform_id(trading: Trading) -> None:
    assert isinstance(trading.last_sent().id, ClientOrderId)
    assert trading.recorded().id == trading.last_sent().id


@then(parsers.parse("l'ordine inviato accetta uno scostamento massimo del {percent:d}% dal prezzo corrente"))
def sent_order_slippage(trading: Trading, percent: int) -> None:
    assert trading.last_sent().slippage == Slippage.percent(Decimal(percent))


@then("l'ordine non è eseguito")
def order_not_executed(trading: Trading) -> None:
    assert trading.order().status is OrderStatus.REJECTED
    assert trading.exchange.positions == {}


@then("l'ordine non è inviato")
def order_not_sent(trading: Trading) -> None:
    assert trading.exchange.sent == []


@then(quoted("l'ordine inviato ha dimensione {size} BTC"))
def sent_order_size(trading: Trading, size: str) -> None:
    assert trading.last_sent().size == Decimal(size)
