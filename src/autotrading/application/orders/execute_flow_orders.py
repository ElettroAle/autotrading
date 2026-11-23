import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from autotrading.application.orders.cancel_protections import CancelProtectionsCommand, CancelProtectionsUseCase
from autotrading.application.orders.errors import ExchangeRejectedOrderError
from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.application.orders.ports import ExchangePort, OrderRepositoryPort, SendingRetryPort
from autotrading.application.orders.protect_flow_position import ProtectFlowPositionCommand, ProtectFlowPositionUseCase
from autotrading.application.orders.sending import OrderSending, RetriedCalls, supported_exchange
from autotrading.application.orders.update_flow_protection import (
    UpdateFlowProtectionCommand,
    UpdateFlowProtectionUseCase,
)
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.failed_order_attempt import FailedOrderAttempt
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, FlowOrder, FlowUpdate, in_sending_order
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
    """The orders sent, in their sending order, the notes of the protection of the positions opened, the closings
    of the positions the exchange would not protect (R3.1.2), and the attempts that failed before an order went through
    (ADR errori-temporanei-ritentati-in-ogni-passo-del-ciclo).
    """

    orders: tuple[Order, ...] = ()
    notes: tuple[ProtectionNote, ...] = ()
    unprotected: frozenset[ClientOrderId] = frozenset()
    failed_attempts: tuple[FailedOrderAttempt, ...] = ()

    @classmethod
    def joined(cls, outcomes: list[FlowOrdersOutcome]) -> FlowOrdersOutcome:
        return cls(
            orders=tuple(order for outcome in outcomes for order in outcome.orders),
            notes=tuple(note for outcome in outcomes for note in outcome.notes),
            unprotected=frozenset(order_id for outcome in outcomes for order_id in outcome.unprotected),
        )


@dataclass(frozen=True, slots=True)
class FlowOrderProtection:
    """Who protects a position a flow opens, who cancels what is left of it when the flow closes it (R3.1.2), and who
    replaces it when the agent updates its exit plan (R3.1.3).
    """

    protect: ProtectFlowPositionUseCase
    cancel: CancelProtectionsUseCase
    update: UpdateFlowProtectionUseCase


@dataclass(frozen=True, slots=True)
class _Sending:
    exchange: ExchangePort
    access: TradingAccess
    command: ExecuteFlowOrdersCommand
    calls: RetriedCalls

    def source(self, order: FlowOrder) -> OrderSource:
        return OrderSource(OrderOrigin.FLOW, flow=FlowLink(self.command.flow_id, self.command.planned_at, order.asset))

    def request(self, order: FlowOrder, leverage: int, market_order: MarketOrder) -> OrderRequest:
        return OrderRequest(self.command.account_id, self.source(order), leverage, market_order)


class ExecuteFlowOrdersUseCase:
    """Sends the orders of a cycle on the account of the flow: the closings first, then the openings (R1.5.5).

    Each order is recorded once with the outcome the exchange gave it (R0.3.4): a refusal is an outcome and the next
    orders go on. A temporary error of the exchange is retried in the same cycle, for the reading, the leverage and the
    sending of the order alone, never for the orders already done; an order that failed is sent again with the same
    client order id only when the exchange does not know it (ADR errori-temporanei-ritentati-in-ogni-passo-del-ciclo).
    So are the access to the account and every placement, update and cancellation of a protection, each on its own
    (ADR protezioni-ritentate-nel-ciclo).
    An exchange that does not answer within the attempts stops the next orders and fails the cycle (R1.2.3).
    An executed opening gets its protection on the exchange, an executed closing leaves none behind (R3.1.2); an
    update replaces the protection of its position (R3.1.3).
    """

    def __init__(  # noqa: PLR0913, PLR0917 - the exchanges and the record of the orders, their protection and retry
        self,
        access: OpenTradingAccessUseCase,
        exchanges: Mapping[str, ExchangePort],
        orders: OrderRepositoryPort,
        slippage: Slippage,
        protection: FlowOrderProtection,
        retry: SendingRetryPort,
    ) -> None:
        self._access = access
        self._exchanges = exchanges
        self._orders = orders
        self._slippage = slippage
        self._protection = protection
        self._retry = retry

    def execute(self, command: ExecuteFlowOrdersCommand) -> FlowOrdersOutcome:
        if not command.orders:
            return FlowOrdersOutcome()
        calls = RetriedCalls(self._retry)
        access = calls.run(None, lambda: self._access.execute(OpenTradingAccessCommand(command.account_id)))
        sending = _Sending(supported_exchange(self._exchanges, access.exchange), access, command, calls)
        outcome = FlowOrdersOutcome.joined(
            [self._executed(sending, order) for order in in_sending_order(command.orders)]
        )
        return replace(outcome, failed_attempts=calls.failed)

    def _executed(self, sending: _Sending, order: FlowOrder) -> FlowOrdersOutcome:
        if isinstance(order, FlowClosing):
            return self._closed(sending, order)
        if isinstance(order, FlowUpdate):
            return self._updated(sending, order)
        return self._opened(sending, order)

    def _updated(self, sending: _Sending, update: FlowUpdate) -> FlowOrdersOutcome:
        """An update sends no order: it replaces the protections the position has waiting (R3.1.3)."""
        command = sending.command
        notes = self._protection.update.execute(
            UpdateFlowProtectionCommand(sending.access, command.account_id, command.flow_id, update, sending.calls)
        )
        return FlowOrdersOutcome(notes=notes)

    def _closed(self, sending: _Sending, closing: FlowClosing) -> FlowOrdersOutcome:
        position = self._retried(
            sending, closing.asset, lambda: sending.exchange.position(sending.access, closing.asset)
        )
        if position is None:
            # Closed on the exchange meanwhile, by a liquidation or by hand: there is nothing left to close.
            operations.info("nessuna posizione da chiudere", extra={"coin": closing.asset})
            return FlowOrdersOutcome()
        request = sending.request(closing, position.leverage, position.closing_order(self._slippage))
        order = self._recorded(self._sent(sending, closing.asset, request))
        if order.execution is not None:
            # A cancellation tried again finds gone what the lost attempt cancelled: the whole of it goes again.
            cancellation = CancelProtectionsCommand(sending.command.account_id, closing.asset)
            self._retried(sending, closing.asset, lambda: self._protection.cancel.execute(cancellation))
        return FlowOrdersOutcome((order,))

    def _opened(self, sending: _Sending, opening: FlowOpening) -> FlowOrdersOutcome:
        market = self._retried(sending, opening.asset, lambda: sending.exchange.market(sending.access, opening.asset))
        market.require_leverage(opening.leverage)
        market_order = MarketOrder.opening(
            opening.asset, opening.direction, market.size_for(opening.value), self._slippage
        )
        request = sending.request(opening, opening.leverage, market_order)
        refusal = self._retried(sending, opening.asset, lambda: _leverage_refusal(sending, opening))
        if refusal is not None:
            return FlowOrdersOutcome((self._recorded(Order.rejected(request, refusal)),))
        order = self._recorded(self._sent(sending, opening.asset, request))
        if order.execution is None:
            return FlowOrdersOutcome((order,))
        return self._protected(sending, opening, order, (order.execution, market))

    def _sent(self, sending: _Sending, asset: str, request: OrderRequest) -> Order:
        return self._retried(sending, asset, OrderSending(sending.exchange, sending.access, request).attempt)

    @staticmethod
    def _retried[T](sending: _Sending, asset: str, call: Callable[[], T]) -> T:
        return sending.calls.run(asset, call)

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
            sending.calls,
        )
        protection = self._protection.protect.execute(command)
        if protection.closing is None:
            return FlowOrdersOutcome((order,), protection.notes)
        closing = protection.closing
        return FlowOrdersOutcome((order, closing), protection.notes, frozenset({closing.id}))


def _leverage_refusal(sending: _Sending, opening: FlowOpening) -> Rejection | None:
    """The leverage the exchange refused is an outcome of the order, not an error to retry."""
    try:
        sending.exchange.set_leverage(sending.access, opening.asset, opening.leverage, MarginMode.per_position())
    except ExchangeRejectedOrderError as error:
        return Rejection.of(error.exchange_message)
    return None
