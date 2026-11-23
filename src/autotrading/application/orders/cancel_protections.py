from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.application.orders.ports import ProtectedPositionPort, ProtectionExchangePort, ProtectionRepositoryPort
from autotrading.application.orders.sending import cancel_protection, supported_exchange


@dataclass(frozen=True, slots=True)
class CancelProtectionsCommand:
    account_id: UUID
    asset: str


class CancelProtectionsUseCase:
    """When a position closes, for any reason, the protections left on the exchange are cancelled and forgotten
    (R3.1.2, ADR ordini-di-protezione-sull-exchange).

    A protection the exchange no longer has, executed or cancelled already, has nothing left to cancel: the whole
    cancellation can go again after a temporary error (ADR protezioni-ritentate-nel-ciclo).
    """

    def __init__(
        self,
        access: OpenTradingAccessUseCase,
        exchanges: Mapping[str, ProtectionExchangePort],
        protections: ProtectionRepositoryPort,
    ) -> None:
        self._access = access
        self._exchanges = exchanges
        self._protections = protections

    def execute(self, position: ProtectedPositionPort) -> None:
        placed = self._protections.placed(position.account_id, position.asset)
        if not placed:
            return
        access = self._access.execute(OpenTradingAccessCommand(position.account_id))
        exchange = supported_exchange(self._exchanges, access.exchange)
        for protection in placed:
            cancel_protection(exchange, access, protection)
        self._protections.remove(position.account_id, position.asset)
