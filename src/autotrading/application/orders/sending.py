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


def supported_exchange(exchanges: Mapping[str, ExchangePort], exchange_name: str) -> ExchangePort:
    exchange = exchanges.get(exchange_name)
    if exchange is None:
        raise UnsupportedOrderExchangeError(exchange_name, exchanges)
    return exchange


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
