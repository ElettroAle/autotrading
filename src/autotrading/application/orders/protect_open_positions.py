from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from autotrading.application.orders.errors import ExchangeRejectedOrderError
from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.application.orders.ports import ExchangePort, ProtectionExchangePort, ProtectionRepositoryPort
from autotrading.application.orders.sending import supported_exchange
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_note import ProtectionNote
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.protection_request import ProtectionRequest
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
    exchange: ExchangePort
    protections: ProtectionExchangePort


class ProtectOpenPositionsUseCase:
    """At every cycle, a position of the flow without a stop loss waiting on the exchange gets the default stop loss of
    the flow on its entry price: the positions opened before the flow had it included (R3.1.2).

    A stop loss the exchange refuses is recorded and tried again at the next cycle.
    """

    def __init__(
        self,
        access: OpenTradingAccessUseCase,
        exchanges: Mapping[str, ExchangePort],
        protection_exchanges: Mapping[str, ProtectionExchangePort],
        protections: ProtectionRepositoryPort,
    ) -> None:
        self._access = access
        self._exchanges = exchanges
        self._protection_exchanges = protection_exchanges
        self._protections = protections

    def execute(self, command: ProtectOpenPositionsCommand) -> tuple[ProtectionNote, ...]:
        access = self._access.execute(OpenTradingAccessCommand(command.account_id))
        account = _Account(
            access,
            supported_exchange(self._exchanges, access.exchange),
            supported_exchange(self._protection_exchanges, access.exchange),
        )
        unprotected = (self._unprotected(account, asset) for asset in command.assets)
        refusals = (self._protected(account, command, position) for position in unprotected if position is not None)
        return tuple(note for note in refusals if note is not None)

    @staticmethod
    def _unprotected(account: _Account, asset: str) -> HeldPosition | None:
        position = account.exchange.position(account.access, asset)
        if position is None:
            return None
        waiting = account.protections.active(account.access, asset)
        if any(protection.kind is ProtectionKind.STOP_LOSS for protection in waiting):
            return None
        return position

    def _protected(
        self, account: _Account, command: ProtectOpenPositionsCommand, position: HeldPosition
    ) -> ProtectionNote | None:
        request = ProtectionRequest(None, None, command.default_stop_loss_percent, None)
        stop = request.levels_at(position.direction, position.entry_price).stop
        market = account.exchange.market(account.access, position.coin)
        order = ProtectionOrder(position.coin, ProtectionKind.STOP_LOSS, position.direction, market.rounded_price(stop))
        try:
            order_id = account.protections.place(account.access, order)
        except ExchangeRejectedOrderError as error:
            return ProtectionNote(position.coin, f"stop loss non piazzato su {position.coin}, {error.exchange_message}")
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
