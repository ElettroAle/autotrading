from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from autotrading.application.orders.errors import ExchangeRejectedOrderError
from autotrading.application.orders.ports import (
    ExchangeConnection,
    OrderRepositoryPort,
    ProtectionExchangePort,
    ProtectionRepositoryPort,
)
from autotrading.application.orders.sending import send_order, supported_exchange
from autotrading.domain.orders.flow_order import FlowOpening
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.order import Order, OrderRequest, OrderSource
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_note import ProtectionNote
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess


@dataclass(frozen=True, slots=True)
class ProtectFlowPositionCommand:
    """An opening of a flow the exchange executed: its account and source, and where the position entered."""

    access: TradingAccess
    account_id: UUID
    flow_id: UUID
    source: OrderSource
    opening: FlowOpening
    entry_price: Decimal
    market: Market


@dataclass(frozen=True, slots=True)
class ProtectionOutcome:
    """What protecting a position left: the closing of a position the exchange would not protect, and the notes."""

    closing: Order | None
    notes: tuple[ProtectionNote, ...]


@dataclass(frozen=True, slots=True)
class _Protection:
    command: ProtectFlowPositionCommand
    exchange: ProtectionExchangePort

    def place(self, kind: ProtectionKind, price: Decimal, protections: ProtectionRepositoryPort) -> None:
        command = self.command
        order = ProtectionOrder(
            command.opening.asset, kind, command.opening.direction, command.market.rounded_price(price)
        )
        order_id = self.exchange.place(command.access, order)
        protections.add(
            PlacedProtection(
                command.account_id,
                command.flow_id,
                order.asset,
                kind,
                order.trigger_price,
                order_id,
                order.client_order_id,
            )
        )


class ProtectFlowPositionUseCase:
    """Places on the exchange the stop loss and, with a target, the take profit of a position a flow just opened
    (R3.1.2, ADR ordini-di-protezione-sull-exchange).

    The levels are those of the exit plan of the agent, else the defaults of the flow on the real entry price. A stop
    loss the exchange refuses closes the position at once: no position of a flow stays without it. A refused take profit
    leaves the position with its stop.
    """

    def __init__(
        self,
        exchanges: Mapping[str, ExchangeConnection],
        protections: ProtectionRepositoryPort,
        orders: OrderRepositoryPort,
        slippage: Slippage,
    ) -> None:
        self._exchanges = exchanges
        self._protections = protections
        self._orders = orders
        self._slippage = slippage

    def execute(self, command: ProtectFlowPositionCommand) -> ProtectionOutcome:
        asset = command.opening.asset
        levels = command.opening.protection.levels_at(command.opening.direction, command.entry_price)
        protection = _Protection(command, supported_exchange(self._exchanges, command.access.exchange).protections)
        notes = tuple(ProtectionNote(asset, note) for note in levels.notes)
        refusal = self._refusal(protection, ProtectionKind.STOP_LOSS, levels.stop)
        if refusal is not None:
            closed = ProtectionNote(asset, f"posizione {asset} chiusa: stop loss non piazzato, {refusal}")
            return ProtectionOutcome(self._closed(command), (*notes, closed))
        if levels.take_profit is None:
            return ProtectionOutcome(None, notes)
        refusal = self._refusal(protection, ProtectionKind.TAKE_PROFIT, levels.take_profit)
        if refusal is None:
            return ProtectionOutcome(None, notes)
        refused = ProtectionNote(asset, f"take profit non piazzato su {asset}, {refusal}")
        return ProtectionOutcome(None, (*notes, refused))

    def _refusal(self, protection: _Protection, kind: ProtectionKind, price: Decimal) -> str | None:
        """The message of the exchange when it refuses the protection, nothing when it places it."""
        try:
            protection.place(kind, price, self._protections)
        except ExchangeRejectedOrderError as error:
            return error.exchange_message
        return None

    def _closed(self, command: ProtectFlowPositionCommand) -> Order | None:
        exchange = supported_exchange(self._exchanges, command.access.exchange)
        position = exchange.account.position(command.access, command.opening.asset)
        if position is None:
            return None
        request = OrderRequest(
            command.account_id, command.source, position.leverage, position.closing_order(self._slippage)
        )
        closing = send_order(exchange.account, command.access, request, exchange.market.market(command.opening.asset))
        self._orders.add(closing)
        return closing
