from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.orders.ports import ExchangePort, TradingAccessPort
from autotrading.application.orders.sending import supported_exchange
from autotrading.domain.orders.market import Market


@dataclass(frozen=True, slots=True)
class ReadMarketCommand:
    account_id: UUID
    coin: str


class ReadMarketUseCase:
    """Reads the rules the exchange of the account sets on an asset now: leverage, size, minimum value (R0.4.1).

    The procedure of verification chooses the value of its opening by them; nothing is sent.
    """

    def __init__(self, access: TradingAccessPort, exchanges: Mapping[str, ExchangePort]) -> None:
        self._access = access
        self._exchanges = exchanges

    def execute(self, command: ReadMarketCommand) -> Market:
        access = self._access.access(command.account_id)
        return supported_exchange(self._exchanges, access.exchange).market(access, command.coin)
