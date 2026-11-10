from decimal import Decimal

from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError, ExchangeUnavailableError
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credentials import Credentials

# What the user reads of a refusal: the text of the exchange with the address masked (R0.2.3).
REDACTED_REJECTION = "User or API Wallet *** does not exist."


def rejection_message(credentials: Credentials) -> str:
    """Hyperliquid names the wallet it does not know: the text of a refusal carries the address sent."""
    return f"User or API Wallet {credentials.account_address.upper()} does not exist."


class FakeExchangeAdapter:
    """An exchange that knows which credentials it accepts and the balance of each account address."""

    def __init__(self) -> None:
        self._balances: dict[Credentials, Balance] = {}
        self.reachable = True
        self.requests: list[Credentials] = []

    def accept(self, credentials: Credentials, amount: Decimal = Decimal("1000.00")) -> None:
        self._balances[credentials] = Balance(amount, "USDC")

    def revoke(self, credentials: Credentials) -> None:
        """The key is deleted or expired on the exchange: from now on it is refused."""
        self._balances.pop(credentials, None)

    def read_balance(self, credentials: Credentials) -> Balance:
        self.requests.append(credentials)
        if not self.reachable:
            raise ExchangeUnavailableError
        balance = self._balances.get(credentials)
        if balance is None:
            raise ExchangeRejectedCredentialsError(rejection_message(credentials))
        return balance
