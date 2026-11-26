from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from autotrading.application.orders.ports import ExchangeConnection, ProtectionExchangePort, ProtectionRepositoryPort
from autotrading.application.orders.sending import (
    ProtectionPlacing,
    RetriedCalls,
    cancel_protection,
    supported_exchange,
)
from autotrading.domain.italian_text import number_text
from autotrading.domain.orders.flow_order import FlowUpdate
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_note import ProtectionNote
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.rejection import Rejection
from autotrading.domain.orders.trading_access import TradingAccess

LEVEL_LABELS = {ProtectionKind.STOP_LOSS: "stop", ProtectionKind.TAKE_PROFIT: "obiettivo"}
NO_LEVEL = "nessuno"


@dataclass(frozen=True, slots=True)
class UpdateFlowProtectionCommand:
    """An update of the exit plan of an open position of a flow, for the account of the flow, with the calls of the
    cycle that retry what fails with a temporary error (ADR protezioni-ritentate-nel-ciclo).
    """

    access: TradingAccess
    account_id: UUID
    flow_id: UUID
    update: FlowUpdate
    calls: RetriedCalls


@dataclass(frozen=True, slots=True)
class _Replacement:
    """The protections of one position, replaced level by level on the exchange and in the record."""

    command: UpdateFlowProtectionCommand
    position: HeldPosition
    market: Market
    exchange: ProtectionExchangePort
    protections: ProtectionRepositoryPort

    def replaced(
        self, kind: ProtectionKind, price: Decimal, previous: PlacedProtection | None
    ) -> tuple[ProtectionNote, ...]:
        """The new protection placed first and the previous one cancelled only after: the position is never left
        without its stop loss. A refusal leaves the previous one in force.
        """
        order = ProtectionOrder(self.position.coin, kind, self.position.direction, self.market.rounded_price(price))
        if previous is not None and previous.trigger_price == order.trigger_price:
            return ()
        placing = ProtectionPlacing(self.exchange, self.command.access, order)
        order_id = self.command.calls.run(order.asset, placing.attempt)
        if isinstance(order_id, Rejection):
            refusal = f"{LEVEL_LABELS[kind]} {order.asset} non aggiornato, {order_id.exchange_message}"
            return (ProtectionNote(order.asset, refusal, refused=True),)
        self.removed(kind, previous)
        self.protections.add(
            PlacedProtection(
                self.command.account_id,
                self.command.flow_id,
                order.asset,
                kind,
                order.trigger_price,
                order_id,
                order.client_order_id,
            )
        )
        return (ProtectionNote(order.asset, _change(kind, order.asset, previous, order.trigger_price)),)

    def removed(self, kind: ProtectionKind, previous: PlacedProtection | None) -> None:
        if previous is None:
            return
        access = self.command.access
        self.command.calls.run(previous.asset, lambda: cancel_protection(self.exchange, access, previous))
        self.protections.remove(self.command.account_id, previous.asset, kind)


class UpdateFlowProtectionUseCase:
    """Replaces on the exchange the stop loss and the take profit of an open position of a flow with the levels of the
    update of its exit plan (R3.1.3, ADR aggiornamento-del-piano-di-uscita-di-una-posizione-aperta).

    A new stop goes back to the default stop of the flow on the entry price of the position when it lies farther; a
    removed target cancels the take profit; the stop loss is never removed. Each change is noted with the level before
    and after, each refusal with the message of the exchange: one stop loss and at most one take profit stay. A
    temporary error is retried in the cycle, the placement and the cancellation each on its own, and a protection tried
    again is never placed twice (ADR protezioni-ritentate-nel-ciclo).
    """

    def __init__(
        self,
        exchanges: Mapping[str, ExchangeConnection],
        protections: ProtectionRepositoryPort,
    ) -> None:
        self._exchanges = exchanges
        self._protections = protections

    def execute(self, command: UpdateFlowProtectionCommand) -> tuple[ProtectionNote, ...]:
        update, access, calls = command.update, command.access, command.calls
        exchange = supported_exchange(self._exchanges, access.exchange)
        position = calls.run(update.asset, lambda: exchange.account.position(access, update.asset))
        if position is None:
            # Closed meanwhile, by its protection or by hand: there is nothing left to protect.
            return ()
        replacement = _Replacement(
            command,
            position,
            calls.run(update.asset, lambda: exchange.market.market(update.asset)),
            exchange.protections,
            self._protections,
        )
        return self._replaced(replacement, update, position)

    def _replaced(
        self, replacement: _Replacement, update: FlowUpdate, position: HeldPosition
    ) -> tuple[ProtectionNote, ...]:
        recorded = self._protections.placed(replacement.command.account_id, update.asset)
        placed = {protection.kind: protection for protection in recorded}
        levels = update.protection.levels_at(position.direction, position.entry_price)
        notes: tuple[ProtectionNote, ...] = ()
        if update.protection.stop is not None:
            stop = ProtectionKind.STOP_LOSS
            limited = tuple(ProtectionNote(update.asset, text) for text in levels.notes)
            notes = (*limited, *replacement.replaced(stop, levels.stop, placed.get(stop)))
        take_profit = ProtectionKind.TAKE_PROFIT
        if levels.take_profit is not None:
            return (*notes, *replacement.replaced(take_profit, levels.take_profit, placed.get(take_profit)))
        previous = placed.get(take_profit)
        if not update.remove_target or previous is None:
            return notes
        replacement.removed(take_profit, previous)
        return (*notes, ProtectionNote(update.asset, _change(take_profit, update.asset, previous, None)))


def _change(kind: ProtectionKind, asset: str, previous: PlacedProtection | None, price: Decimal | None) -> str:
    before = NO_LEVEL if previous is None else number_text(previous.trigger_price)
    after = NO_LEVEL if price is None else number_text(price)
    return f"{LEVEL_LABELS[kind]} {asset} da {before} a {after}"
