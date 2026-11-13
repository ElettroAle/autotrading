from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.application.orders.ports import ExchangePort, OrderRepositoryPort
from autotrading.application.orders.sending import send_order, supported_exchange
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderRequest, OrderSource
from autotrading.domain.orders.slippage import Slippage


@dataclass(frozen=True, slots=True)
class OpenPositionCommand:
    account_id: UUID
    coin: str
    direction: Direction
    leverage: int
    value: Decimal
    source: OrderSource


class OpenPositionUseCase:
    """Opens a position at the market price within the slippage (R0.3.1); not a command of the user.

    The procedure of verification, and later the flows, use it. A leverage beyond the maximum of the asset sends
    nothing; otherwise the order is sent once and recorded with the outcome the exchange gave it (R0.3.3, R0.3.4).
    """

    def __init__(
        self,
        access: OpenTradingAccessUseCase,
        exchanges: Mapping[str, ExchangePort],
        orders: OrderRepositoryPort,
        slippage: Slippage,
    ) -> None:
        self._access = access
        self._exchanges = exchanges
        self._orders = orders
        self._slippage = slippage

    def execute(self, command: OpenPositionCommand) -> Order:
        access = self._access.execute(OpenTradingAccessCommand(command.account_id))
        exchange = supported_exchange(self._exchanges, access.exchange)
        market = exchange.market(access, command.coin)
        market.require_leverage(command.leverage)
        market_order = MarketOrder.opening(
            command.coin, command.direction, market.size_for(command.value), self._slippage
        )
        exchange.set_leverage(access, command.coin, command.leverage)
        order = send_order(
            exchange, access, OrderRequest(command.account_id, command.source, command.leverage, market_order)
        )
        self._orders.add(order)
        return order
