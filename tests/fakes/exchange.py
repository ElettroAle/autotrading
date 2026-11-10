from decimal import Decimal

from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError, ExchangeUnavailableError
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credentials import Credentials

REJECTION_MESSAGE = "User or API Wallet 0x0000000000000000000000000000000000000000 does not exist."


class FakeExchangeAdapter:
    """An exchange that knows which credentials it accepts and the balance of each account address."""

    def __init__(self) -> None:
        self._balances: dict[Credentials, Balance] = {}
        self.reachable = True
        self.requests: list[Credentials] = []

    def accept(self, credentials: Credentials, amount: Decimal = Decimal("1000.00")) -> None:
        self._balances[credentials] = Balance(amount, "USDC")

    def read_balance(self, credentials: Credentials) -> Balance:
        self.requests.append(credentials)
        if not self.reachable:
            raise ExchangeUnavailableError
        balance = self._balances.get(credentials)
        if balance is None:
            raise ExchangeRejectedCredentialsError(REJECTION_MESSAGE)
        return balance
