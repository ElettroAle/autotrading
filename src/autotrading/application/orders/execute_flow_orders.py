import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.orders.cancel_protections import CancelProtectionsCommand, CancelProtectionsUseCase
from autotrading.application.orders.errors import ExchangeRejectedOrderError
from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.application.orders.ports import ExchangePort, OrderRepositoryPort
from autotrading.application.orders.protect_flow_position import ProtectFlowPositionCommand, ProtectFlowPositionUseCase
from autotrading.application.orders.sending import send_order, supported_exchange
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, FlowOrder, in_sending_order
from autotrading.domain.orders.margin_mode import MarginMode
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.protection_note import ProtectionNote
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
class FlowOrdersOutcome:
    """The orders sent, in their sending order, the notes of the protection of the positions opened, and the closings
    of the positions the exchange would not protect (R3.1.2).
    """

    orders: tuple[Order, ...] = ()
    notes: tuple[ProtectionNote, ...] = ()
    unprotected: frozenset[ClientOrderId] = frozenset()

    @classmethod
    def joined(cls, outcomes: list[FlowOrdersOutcome]) -> FlowOrdersOutcome:
        return cls(
            orders=tuple(order for outcome in outcomes for order in outcome.orders),
            notes=tuple(note for outcome in outcomes for note in outcome.notes),
            unprotected=frozenset(order_id for outcome in outcomes for order_id in outcome.unprotected),
        )


@dataclass(frozen=True, slots=True)
class FlowOrderProtection:
    """Who protects a position a flow opens, and who cancels what is left of it when the flow closes it (R3.1.2)."""

    protect: ProtectFlowPositionUseCase
    cancel: CancelProtectionsUseCase


@dataclass(frozen=True, slots=True)
class _Sending:
    exchange: ExchangePort
    access: TradingAccess
    command: ExecuteFlowOrdersCommand

    def source(self, order: FlowOrder) -> OrderSource:
        return OrderSource(OrderOrigin.FLOW, flow=FlowLink(self.command.flow_id, self.command.planned_at, order.asset))

    def request(self, order: FlowOrder, leverage: int, market_order: MarketOrder) -> OrderRequest:
        return OrderRequest(self.command.account_id, self.source(order), leverage, market_order)


class ExecuteFlowOrdersUseCase:
    """Sends the orders of a cycle on the account of the flow: the closings first, then the openings (R1.5.5).

    Each order is sent once and recorded at once with the outcome the exchange gave it (R0.3.3, R0.3.4): a refusal
    is an outcome and the next orders go on; an exchange that does not answer stops them and fails the cycle (R1.2.3).
    An executed opening gets its protection on the exchange, an executed closing leaves none behind (R3.1.2).
    """

    def __init__(
        self,
        access: OpenTradingAccessUseCase,
        exchanges: Mapping[str, ExchangePort],
        orders: OrderRepositoryPort,
        slippage: Slippage,
        protection: FlowOrderProtection,
    ) -> None:
        self._access = access
        self._exchanges = exchanges
        self._orders = orders
        self._slippage = slippage
        self._protection = protection

    def execute(self, command: ExecuteFlowOrdersCommand) -> FlowOrdersOutcome:
        if not command.orders:
            return FlowOrdersOutcome()
        access = self._access.execute(OpenTradingAccessCommand(command.account_id))
        sending = _Sending(supported_exchange(self._exchanges, access.exchange), access, command)
        return FlowOrdersOutcome.joined([self._executed(sending, order) for order in in_sending_order(command.orders)])

    def _executed(self, sending: _Sending, order: FlowOrder) -> FlowOrdersOutcome:
        if isinstance(order, FlowClosing):
            return self._closed(sending, order)
        return self._opened(sending, order)

    def _closed(self, sending: _Sending, closing: FlowClosing) -> FlowOrdersOutcome:
        position = sending.exchange.position(sending.access, closing.asset)
        if position is None:
            # Closed on the exchange meanwhile, by a liquidation or by hand: there is nothing left to close.
            operations.info("nessuna posizione da chiudere", extra={"coin": closing.asset})
            return FlowOrdersOutcome()
        request = sending.request(closing, position.leverage, position.closing_order(self._slippage))
        order = self._recorded(send_order(sending.exchange, sending.access, request))
        if order.execution is not None:
            self._protection.cancel.execute(CancelProtectionsCommand(sending.command.account_id, closing.asset))
        return FlowOrdersOutcome((order,))

    def _opened(self, sending: _Sending, opening: FlowOpening) -> FlowOrdersOutcome:
        market = sending.exchange.market(sending.access, opening.asset)
        market.require_leverage(opening.leverage)
        market_order = MarketOrder.opening(
            opening.asset, opening.direction, market.size_for(opening.value), self._slippage
        )
        request = sending.request(opening, opening.leverage, market_order)
        try:
            sending.exchange.set_leverage(sending.access, opening.asset, opening.leverage, MarginMode.per_position())
        except ExchangeRejectedOrderError as error:
            return FlowOrdersOutcome((self._recorded(Order.rejected(request, Rejection.of(error.exchange_message))),))
        order = self._recorded(send_order(sending.exchange, sending.access, request))
        if order.execution is None:
            return FlowOrdersOutcome((order,))
        return self._protected(sending, opening, order, (order.execution, market))

    def _recorded(self, order: Order) -> Order:
        self._orders.add(order)
        return order

    def _protected(
        self, sending: _Sending, opening: FlowOpening, order: Order, executed: tuple[Execution, Market]
    ) -> FlowOrdersOutcome:
        execution, market = executed
        command = ProtectFlowPositionCommand(
            sending.access,
            sending.command.account_id,
            sending.command.flow_id,
            sending.source(opening),
            opening,
            execution.average_price,
            market,
        )
        protection = self._protection.protect.execute(command)
        if protection.closing is None:
            return FlowOrdersOutcome((order,), protection.notes)
        closing = protection.closing
        return FlowOrdersOutcome((order, closing), protection.notes, frozenset({closing.id}))
