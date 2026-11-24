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
    is opened (R0.1.3). An account of an exchange without credentials has nothing to open: its identifier reaches it
    (R6.3.2).
    """

    def __init__(self, accounts: OrderAccountPort, opener: AccessOpenerPort) -> None:
        self._accounts = accounts
        self._opener = opener

    def execute(self, command: OpenTradingAccessCommand) -> TradingAccess:
        sealed = self._accounts.sealed_access(command.account_id)
        if not sealed.has_credentials:
            return TradingAccess.without_credentials(sealed.exchange, sealed.account_id)
        return self._opener.open_access(sealed)
