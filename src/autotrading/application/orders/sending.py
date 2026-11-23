from collections.abc import Mapping

from autotrading.application.orders.errors import (
    ExchangeRejectedOrderError,
    OrderNotAcknowledgedError,
    UnsupportedOrderExchangeError,
)
from autotrading.application.orders.ports import ExchangePort
from autotrading.domain.orders.order import Order, OrderRequest
from autotrading.domain.orders.rejection import Rejection
from autotrading.domain.orders.trading_access import TradingAccess


def supported_exchange[E](exchanges: Mapping[str, E], exchange_name: str) -> E:
    exchange = exchanges.get(exchange_name)
    if exchange is None:
        raise UnsupportedOrderExchangeError(exchange_name, exchanges)
    return exchange


class OrderSending:
    """One order of a cycle sent until the exchange answers, always with the same client order id (ADR
    errori-temporanei-ritentati-in-ogni-passo-del-ciclo).

    An attempt that failed may have reached the exchange: before the order goes again the exchange is asked for it by
    its client order id, and an order it knows is never sent twice. Only an order it does not know goes again.
    """

    def __init__(self, exchange: ExchangePort, access: TradingAccess, request: OrderRequest) -> None:
        self._exchange = exchange
        self._access = access
        self._request = request
        self._tried = False

    def attempt(self) -> Order:
        if self._tried:
            known = self._exchange.find_order(self._access, self._request.market_order)
            if known is not None:
                return Order.executed(self._request, known)
        self._tried = True
        return send_order(self._exchange, self._access, self._request)


def send_order(exchange: ExchangePort, access: TradingAccess, request: OrderRequest) -> Order:
    """Sends the order once, never again: a refusal is an outcome, an order without answer is looked up (R0.3.3)."""
    try:
        return Order.executed(request, exchange.place_market_order(access, request.market_order))
    except ExchangeRejectedOrderError as error:
        return Order.rejected(request, Rejection.of(error.exchange_message))
    except OrderNotAcknowledgedError:
        return _looked_up(exchange, access, request)


def _looked_up(exchange: ExchangePort, access: TradingAccess, request: OrderRequest) -> Order:
    execution = exchange.find_order(access, request.market_order)
    return Order.unknown(request) if execution is None else Order.executed(request, execution)
