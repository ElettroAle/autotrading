from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.application.orders.ports import ExchangeConnection, ProtectionRepositoryPort, SendingRetryPort
from autotrading.application.orders.sending import (
    ProtectionPlacing,
    RetriedCalls,
    held_protections,
    supported_exchange,
)
from autotrading.domain.orders.failed_order_attempt import FailedOrderAttempt
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_note import ProtectionNote
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.protection_request import ProtectionRequest
from autotrading.domain.orders.rejection import Rejection
from autotrading.domain.orders.trading_access import TradingAccess


@dataclass(frozen=True, slots=True)
class ProtectOpenPositionsCommand:
    """The flow at the start of the execution of the orders of its cycle: its account, assets and default stop loss."""

    account_id: UUID
    flow_id: UUID
    assets: tuple[str, ...]
    default_stop_loss_percent: Decimal


@dataclass(frozen=True, slots=True)
class _Account:
    access: TradingAccess
    exchange: ExchangeConnection
    calls: RetriedCalls


class ProtectOpenPositionsUseCase:
    """At every cycle, a position of the flow without a stop loss waiting on the exchange gets the default stop loss of
    the flow on its entry price: the positions opened before the flow had it included (R3.1.2).

    A stop loss the exchange refuses is recorded and tried again at the next cycle. A temporary error is retried in the
    cycle, and a stop loss tried again is never placed twice (ADR protezioni-ritentate-nel-ciclo): what the use case
    returns is what the cycle records, the notes of the refusals and the attempts that failed.
    """

    def __init__(
        self,
        access: OpenTradingAccessUseCase,
        exchanges: Mapping[str, ExchangeConnection],
        protections: ProtectionRepositoryPort,
        retry: SendingRetryPort,
    ) -> None:
        self._access = access
        self._exchanges = exchanges
        self._protections = protections
        self._retry = retry

    def execute(self, command: ProtectOpenPositionsCommand) -> tuple[ProtectionNote | FailedOrderAttempt, ...]:
        calls = RetriedCalls(self._retry)
        access = calls.run(None, lambda: self._access.execute(OpenTradingAccessCommand(command.account_id)))
        account = _Account(access, supported_exchange(self._exchanges, access.exchange), calls)
        unprotected = (self._unprotected(account, asset) for asset in command.assets)
        refusals = (self._protected(account, command, position) for position in unprotected if position is not None)
        notes = tuple(note for note in refusals if note is not None)
        return (*notes, *calls.failed)

    @staticmethod
    def _unprotected(account: _Account, asset: str) -> HeldPosition | None:
        held = account.calls.run(asset, lambda: held_protections(account.exchange, account.access, asset))
        if held is None or held.has_stop_loss:
            return None
        return held.position

    def _protected(
        self, account: _Account, command: ProtectOpenPositionsCommand, position: HeldPosition
    ) -> ProtectionNote | None:
        request = ProtectionRequest(None, None, command.default_stop_loss_percent, None)
        stop = request.levels_at(position.direction, position.entry_price).stop
        market = account.calls.run(position.coin, lambda: account.exchange.market.market(position.coin))
        order = ProtectionOrder(position.coin, ProtectionKind.STOP_LOSS, position.direction, market.rounded_price(stop))
        placing = ProtectionPlacing(account.exchange.protections, account.access, order)
        order_id = account.calls.run(position.coin, placing.attempt)
        if isinstance(order_id, Rejection):
            refusal = order_id.exchange_message
            return ProtectionNote(position.coin, f"stop loss non piazzato su {position.coin}, {refusal}")
        self._protections.add(
            PlacedProtection(
                command.account_id,
                command.flow_id,
                position.coin,
                order.kind,
                order.trigger_price,
                order_id,
                order.client_order_id,
            )
        )
        return None
