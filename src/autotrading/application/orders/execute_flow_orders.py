import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.orders.errors import ExchangeRejectedOrderError
from autotrading.application.orders.ports import ExchangePort, OrderRepositoryPort, TradingAccessPort
from autotrading.application.orders.sending import send_order, supported_exchange
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, FlowOrder, in_sending_order
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.rejection import Rejection
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess

operations = logging.getLogger("autotrading.orders")


@dataclass(frozen=True, slots=True)
class ExecuteFlowOrdersCommand:
    """The orders a cycle of a flow got through the risk check, for the account of the flow."""

    account_id: UUID
    flow_id: UUID
    planned_at: datetime
    orders: tuple[FlowOrder, ...]


@dataclass(frozen=True, slots=True)
class _Sending:
    exchange: ExchangePort
    access: TradingAccess
    command: ExecuteFlowOrdersCommand

    def request(self, order: FlowOrder, leverage: int, market_order: MarketOrder) -> OrderRequest:
        link = FlowLink(self.command.flow_id, self.command.planned_at, order.asset)
        return OrderRequest(self.command.account_id, OrderSource(OrderOrigin.FLOW, flow=link), leverage, market_order)


class ExecuteFlowOrdersUseCase:
    """Sends the orders of a cycle on the account of the flow: the closings first, then the openings (R1.5.5).

    Each order is sent once and recorded at once with the outcome the exchange gave it (R0.3.3, R0.3.4): a refusal
    is an outcome and the next orders go on; an exchange that does not answer stops them and fails the cycle (R1.2.3).
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

    def execute(self, command: ExecuteFlowOrdersCommand) -> tuple[Order, ...]:
        if not command.orders:
            return ()
        access = self._access.access(command.account_id)
        sending = _Sending(supported_exchange(self._exchanges, access.exchange), access, command)
        executed = (self._executed(sending, order) for order in in_sending_order(command.orders))
        return tuple(order for order in executed if order is not None)

    def _executed(self, sending: _Sending, order: FlowOrder) -> Order | None:
        sent = self._closed(sending, order) if isinstance(order, FlowClosing) else self._opened(sending, order)
        if sent is not None:
            self._orders.add(sent)
        return sent

    def _closed(self, sending: _Sending, closing: FlowClosing) -> Order | None:
        position = sending.exchange.position(sending.access, closing.asset)
        if position is None:
            # Closed on the exchange meanwhile, by a liquidation or by hand: there is nothing left to close.
            operations.info("nessuna posizione da chiudere", extra={"coin": closing.asset})
            return None
        request = sending.request(closing, position.leverage, position.closing_order(self._slippage))
        return send_order(sending.exchange, sending.access, request)

    def _opened(self, sending: _Sending, opening: FlowOpening) -> Order:
        market = sending.exchange.market(sending.access, opening.asset)
        market.require_leverage(opening.leverage)
        market_order = MarketOrder.opening(
            opening.asset, opening.direction, market.size_for(opening.value), self._slippage
        )
        request = sending.request(opening, opening.leverage, market_order)
        try:
            sending.exchange.set_leverage(sending.access, opening.asset, opening.leverage)
        except ExchangeRejectedOrderError as error:
            return Order.rejected(request, Rejection.of(error.exchange_message))
        return send_order(sending.exchange, sending.access, request)
