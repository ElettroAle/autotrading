from datetime import UTC, datetime
from decimal import Decimal

from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError, ExchangeUnavailableError
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.position import Position

# What the user reads of a refusal: the text of the exchange with the address masked (R0.2.3).
REDACTED_REJECTION = "User or API Wallet *** does not exist."
READ_AT = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def rejection_message(credentials: Credentials) -> str:
    """Hyperliquid names the wallet it does not know: the text of a refusal carries the address sent."""
    return f"User or API Wallet {credentials.account_address.upper()} does not exist."


class FakeExchangeAdapter:
    """An exchange that knows which credentials it accepts and the state of each account behind them."""

    def __init__(self) -> None:
        self._states: dict[Credentials, AccountState] = {}
        self.reachable = True
        self.requests: list[Credentials] = []

    def accept(self, credentials: Credentials, amount: Decimal = Decimal("1000.00")) -> None:
        balance = Balance(amount, "USDC")
        self._states[credentials] = AccountState(balance, balance, (), READ_AT)

    def open_position(self, credentials: Credentials, position: Position) -> None:
        state = self._states[credentials]
        self._states[credentials] = AccountState(
            state.balance, state.available_margin, (*state.positions, position), state.read_at
        )

    def revoke(self, credentials: Credentials) -> None:
        """The key is deleted or expired on the exchange: from now on it is refused."""
        self._states.pop(credentials, None)

    def read_state(self, credentials: Credentials) -> AccountState:
        self.requests.append(credentials)
        if not self.reachable:
            raise ExchangeUnavailableError
        state = self._states.get(credentials)
        if state is None:
            raise ExchangeRejectedCredentialsError(rejection_message(credentials))
        return state
