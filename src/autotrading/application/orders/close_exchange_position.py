from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.orders.errors import NoOpenPositionError
from autotrading.application.orders.ports import ExchangePort, OrderRepositoryPort, TradingAccessPort
from autotrading.application.orders.sending import send_order, supported_exchange
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.user_id import UserId


@dataclass(frozen=True, slots=True)
class CloseExchangePositionCommand:
    account_id: UUID
    coin: str
    user_id: UserId


class CloseExchangePositionUseCase:
    """Closes in the worker the whole position on an asset, at a manual command of a user (R0.3.2, ADR 0023).

    Without a position on the asset nothing is sent; otherwise the reduce-only order is sent once and recorded with
    the manual origin and the user who asked.
    """

    def __init__(
        self,
        access: TradingAccessPort,
        exchanges: Mapping[str, ExchangePort],
        orders: OrderRepositoryPort,
        slippage: Slippage,
    ) -> None:
        self._access = access
        self._exchanges = exchanges
        self._orders = orders
        self._slippage = slippage

    def execute(self, command: CloseExchangePositionCommand) -> Order:
        access = self._access.access(command.account_id)
        exchange = supported_exchange(self._exchanges, access.exchange)
        position = _open_position(exchange, access, command.coin)
        source = OrderSource(OrderOrigin.MANUAL, command.user_id.value)
        request = OrderRequest(command.account_id, source, position.leverage, position.closing_order(self._slippage))
        order = send_order(exchange, access, request)
        self._orders.add(order)
        return order


def _open_position(exchange: ExchangePort, access: TradingAccess, coin: str) -> HeldPosition:
    position = exchange.position(access, coin)
    if position is None:
        raise NoOpenPositionError(coin)
    return position
