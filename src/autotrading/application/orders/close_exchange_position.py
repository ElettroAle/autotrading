from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.orders.cancel_protections import CancelProtectionsCommand, CancelProtectionsUseCase
from autotrading.application.orders.errors import NoOpenPositionError
from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.application.orders.ports import ExchangePort, OrderRepositoryPort
from autotrading.application.orders.sending import send_order, supported_exchange
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.order import Order, OrderRequest, OrderSource
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess


@dataclass(frozen=True, slots=True)
class CloseExchangePositionCommand:
    account_id: UUID
    coin: str
    # Who asks and why: a user with a manual command, for the flow whose position it closes if any, or the procedure of
    # verification it launched.
    source: OrderSource


class CloseExchangePositionUseCase:
    """Closes in the worker the whole position on an asset, at a manual command of a user or for the
    procedure of verification (R0.3.2, R0.4.1, ADR 0023, ADR 0024).

    Without a position on the asset nothing is sent; otherwise the reduce-only order is sent once and recorded with
    the source of the command. An executed closing leaves no protection of a flow behind on the exchange (R3.1.2).
    """

    def __init__(
        self,
        access: OpenTradingAccessUseCase,
        exchanges: Mapping[str, ExchangePort],
        orders: OrderRepositoryPort,
        slippage: Slippage,
        protections: CancelProtectionsUseCase,
    ) -> None:
        self._access = access
        self._exchanges = exchanges
        self._orders = orders
        self._slippage = slippage
        self._protections = protections

    def execute(self, command: CloseExchangePositionCommand) -> Order:
        access = self._access.execute(OpenTradingAccessCommand(command.account_id))
        exchange = supported_exchange(self._exchanges, access.exchange)
        position = _open_position(exchange, access, command.coin)
        closing = position.closing_order(self._slippage)
        request = OrderRequest(command.account_id, command.source, position.leverage, closing)
        order = send_order(exchange, access, request)
        self._orders.add(order)
        if order.execution is not None:
            self._protections.execute(CancelProtectionsCommand(command.account_id, command.coin))
        return order


def _open_position(exchange: ExchangePort, access: TradingAccess, coin: str) -> HeldPosition:
    position = exchange.position(access, coin)
    if position is None:
        raise NoOpenPositionError(coin)
    return position
