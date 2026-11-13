from dataclasses import dataclass
from uuid import UUID

from autotrading.application.orders.ports import AccessOpenerPort, OrderAccountPort
from autotrading.domain.orders.trading_access import TradingAccess


@dataclass(frozen=True, slots=True)
class OpenTradingAccessCommand:
    account_id: UUID


class OpenTradingAccessUseCase:
    """What signs the orders of an account of the tenant (ADR 0023).

    The account is looked up for the tenant first, so an account the tenant does not have is not found before anything
    is opened (R0.1.3).
    """

    def __init__(self, accounts: OrderAccountPort, opener: AccessOpenerPort) -> None:
        self._accounts = accounts
        self._opener = opener

    def execute(self, command: OpenTradingAccessCommand) -> TradingAccess:
        return self._opener.open_access(self._accounts.sealed_access(command.account_id))
