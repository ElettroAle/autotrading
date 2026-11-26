from collections.abc import Callable, Mapping

from autotrading.application.orders.errors import (
    ExchangeRejectedOrderError,
    OrderNotAcknowledgedError,
    UnsupportedOrderExchangeError,
)
from autotrading.application.orders.ports import (
    ExchangeConnection,
    OrderExchangePort,
    ProtectionExchangePort,
    SendingRetryPort,
)
from autotrading.domain.orders.failed_order_attempt import FailedOrderAttempt
from autotrading.domain.orders.held_protections import HeldProtections
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.order import Order, OrderRequest
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.rejection import Rejection
from autotrading.domain.orders.trading_access import TradingAccess


def supported_exchange[E](exchanges: Mapping[str, E], exchange_name: str) -> E:
    exchange = exchanges.get(exchange_name)
    if exchange is None:
        raise UnsupportedOrderExchangeError(exchange_name, exchanges)
    return exchange


class RetriedCalls:
    """The calls of the orders of one cycle to the exchange and to the account, each made again after a temporary error
    (ADR errori-temporanei-ritentati-in-ogni-passo-del-ciclo, ADR protezioni-ritentate-nel-ciclo).

    Every attempt that failed stays, named by its asset when it has one, for the record of the cycle.
    """

    def __init__(self, retry: SendingRetryPort) -> None:
        self._retry = retry
        self._failed: list[FailedOrderAttempt] = []

    @property
    def failed(self) -> tuple[FailedOrderAttempt, ...]:
        return tuple(self._failed)

    def run[T](self, asset: str | None, call: Callable[[], T]) -> T:
        return self._retry.run(
            call, lambda attempt, error: self._failed.append(FailedOrderAttempt.of(asset, attempt, error))
        )


class OrderSending:
    """One order of a cycle sent until the exchange answers, always with the same client order id (ADR
    errori-temporanei-ritentati-in-ogni-passo-del-ciclo).

    An attempt that failed may have reached the exchange: before the order goes again the exchange is asked for it by
    its client order id, and an order it knows is never sent twice. Only an order it does not know goes again.
    """

    def __init__(
        self, exchange: OrderExchangePort, access: TradingAccess, request: OrderRequest, market: Market
    ) -> None:
        self._exchange = exchange
        self._access = access
        self._request = request
        self._market = market
        self._tried = False

    def attempt(self) -> Order:
        if self._tried:
            known = self._exchange.find_order(self._access, self._request.market_order)
            if known is not None:
                return Order.executed(self._request, known)
        self._tried = True
        return send_order(self._exchange, self._access, self._request, self._market)


class ProtectionPlacing:
    """One stop loss or take profit of a cycle placed until the exchange answers, always with the same client order id
    (ADR protezioni-ritentate-nel-ciclo).

    An attempt that failed may have reached the exchange: before the protection goes again the exchange is asked for it
    by its client order id, and a protection it knows is never placed twice. A refusal is an outcome, never tried again
    (R0.3.3).
    """

    def __init__(self, exchange: ProtectionExchangePort, access: TradingAccess, order: ProtectionOrder) -> None:
        self._exchange = exchange
        self._access = access
        self._order = order
        self._tried = False

    def attempt(self) -> str | Rejection:
        """The identifier the exchange gave the protection, or its refusal."""
        if self._tried:
            known = self._exchange.find(self._access, self._order)
            if known is not None:
                return known
        self._tried = True
        try:
            return self._exchange.place(self._access, self._order)
        except ExchangeRejectedOrderError as error:
            return Rejection.of(error.exchange_message)


def held_protections(exchange: ExchangeConnection, access: TradingAccess, asset: str) -> HeldProtections | None:
    """The position of the account on the asset with the protections waiting for it, or None without a position: the
    one reading of the protections on the exchange of a position (R3.1.2, R5.5.3).
    """
    position = exchange.account.position(access, asset)
    if position is None:
        return None
    return HeldProtections(position, exchange.protections.active(access, asset))


def cancel_protection(exchange: ProtectionExchangePort, access: TradingAccess, protection: PlacedProtection) -> None:
    """A protection executed or cancelled already, also by an attempt whose answer was lost, has nothing left to
    cancel, only to forget.
    """
    try:
        exchange.cancel(access, protection.asset, protection.exchange_order_id)
    except ExchangeRejectedOrderError:
        return


def send_order(exchange: OrderExchangePort, access: TradingAccess, request: OrderRequest, market: Market) -> Order:
    """Sends the order once, never again: a refusal is an outcome, an order without answer is looked up (R0.3.3)."""
    try:
        return Order.executed(request, exchange.place_market_order(access, request.market_order, market))
    except ExchangeRejectedOrderError as error:
        return Order.rejected(request, Rejection.of(error.exchange_message))
    except OrderNotAcknowledgedError:
        return _looked_up(exchange, access, request)


def _looked_up(exchange: OrderExchangePort, access: TradingAccess, request: OrderRequest) -> Order:
    execution = exchange.find_order(access, request.market_order)
    return Order.unknown(request) if execution is None else Order.executed(request, execution)
