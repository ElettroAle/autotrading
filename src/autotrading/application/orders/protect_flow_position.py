from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from autotrading.application.orders.ports import (
    ExchangePort,
    OrderRepositoryPort,
    ProtectionExchangePort,
    ProtectionRepositoryPort,
)
from autotrading.application.orders.sending import OrderSending, ProtectionPlacing, RetriedCalls, supported_exchange
from autotrading.domain.orders.flow_order import FlowOpening
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.order import Order, OrderRequest, OrderSource
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_note import ProtectionNote
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.rejection import Rejection
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess


@dataclass(frozen=True, slots=True)
class ProtectFlowPositionCommand:
    """An opening of a flow the exchange executed: its account and source, where the position entered, and the calls of
    the cycle that retry what fails with a temporary error (ADR protezioni-ritentate-nel-ciclo).
    """

    access: TradingAccess
    account_id: UUID
    flow_id: UUID
    source: OrderSource
    opening: FlowOpening
    entry_price: Decimal
    market: Market
    calls: RetriedCalls


@dataclass(frozen=True, slots=True)
class ProtectionOutcome:
    """What protecting a position left: the closing of a position the exchange would not protect, and the notes."""

    closing: Order | None
    notes: tuple[ProtectionNote, ...]


@dataclass(frozen=True, slots=True)
class _Protection:
    command: ProtectFlowPositionCommand
    exchange: ProtectionExchangePort

    def refusal(self, kind: ProtectionKind, price: Decimal, protections: ProtectionRepositoryPort) -> str | None:
        """The message of the exchange when it refuses the protection, nothing when it places it."""
        command = self.command
        order = ProtectionOrder(
            command.opening.asset, kind, command.opening.direction, command.market.rounded_price(price)
        )
        placing = ProtectionPlacing(self.exchange, command.access, order)
        order_id = command.calls.run(order.asset, placing.attempt)
        if isinstance(order_id, Rejection):
            return order_id.exchange_message
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
        return None


class ProtectFlowPositionUseCase:
    """Places on the exchange the stop loss and, with a target, the take profit of a position a flow just opened
    (R3.1.2, ADR ordini-di-protezione-sull-exchange).

    The levels are those of the exit plan of the agent, else the defaults of the flow on the real entry price. A stop
    loss the exchange refuses closes the position at once: no position of a flow stays without it. A refused take profit
    leaves the position with its stop. A temporary error is retried in the cycle, and a protection or a closing tried
    again is never sent twice (ADR protezioni-ritentate-nel-ciclo).
    """

    def __init__(
        self,
        exchanges: Mapping[str, ExchangePort],
        protection_exchanges: Mapping[str, ProtectionExchangePort],
        protections: ProtectionRepositoryPort,
        orders: OrderRepositoryPort,
        slippage: Slippage,
    ) -> None:
        self._exchanges = exchanges
        self._protection_exchanges = protection_exchanges
        self._protections = protections
        self._orders = orders
        self._slippage = slippage

    def execute(self, command: ProtectFlowPositionCommand) -> ProtectionOutcome:
        asset = command.opening.asset
        levels = command.opening.protection.levels_at(command.opening.direction, command.entry_price)
        protection = _Protection(command, supported_exchange(self._protection_exchanges, command.access.exchange))
        notes = tuple(ProtectionNote(asset, note) for note in levels.notes)
        refusal = protection.refusal(ProtectionKind.STOP_LOSS, levels.stop, self._protections)
        if refusal is not None:
            closed = ProtectionNote(asset, f"posizione {asset} chiusa: stop loss non piazzato, {refusal}")
            return ProtectionOutcome(self._closed(command), (*notes, closed))
        if levels.take_profit is None:
            return ProtectionOutcome(None, notes)
        refusal = protection.refusal(ProtectionKind.TAKE_PROFIT, levels.take_profit, self._protections)
        if refusal is None:
            return ProtectionOutcome(None, notes)
        refused = ProtectionNote(asset, f"take profit non piazzato su {asset}, {refusal}")
        return ProtectionOutcome(None, (*notes, refused))

    def _closed(self, command: ProtectFlowPositionCommand) -> Order | None:
        exchange = supported_exchange(self._exchanges, command.access.exchange)
        asset = command.opening.asset
        position = command.calls.run(asset, lambda: exchange.position(command.access, asset))
        if position is None:
            return None
        request = OrderRequest(
            command.account_id, command.source, position.leverage, position.closing_order(self._slippage)
        )
        closing = command.calls.run(asset, OrderSending(exchange, command.access, request).attempt)
        self._orders.add(closing)
        return closing
