from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError, ExchangeUnavailableError
from autotrading.application.flows.errors import FlowCredentialsRefusedError, FlowExchangeUnavailableError
from autotrading.application.verification.errors import (
    VerificationCredentialsRejectedError,
    VerificationExchangeUnavailableError,
)
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.flows.cycle_access import CycleAccess
from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.verification.reading import AccountReading, PositionReading
from autotrading.domain.verification.verification_access import VerificationAccess
from tests.fakes.order_exchange import FakeOrderExchangeAdapter

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
        self.shown: dict[Credentials, list[AccountState]] = {}
        self._orders: FakeOrderExchangeAdapter | None = None

    def trades_on(self, orders: FakeOrderExchangeAdapter) -> None:
        """The same exchange for orders: the positions it holds for an account are part of its state."""
        self._orders = orders

    def accept(self, credentials: Credentials, amount: Decimal = Decimal("1000.00")) -> None:
        balance = Balance(amount, "USDC")
        self._states[credentials] = AccountState(balance, balance, (), READ_AT)

    def open_position(self, credentials: Credentials, position: Position) -> None:
        state = self._states[credentials]
        self._states[credentials] = AccountState(
            state.balance, state.available_margin, (*state.positions, position), state.read_at
        )

    def set_available_margin(self, credentials: Credentials, amount: Decimal) -> None:
        state = self._states[credentials]
        self._states[credentials] = replace(state, available_margin=Balance(amount, state.balance.currency))

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
        shown = replace(state, positions=(*state.positions, *self._traded_positions(credentials)))
        self.shown.setdefault(credentials, []).append(shown)
        return shown

    def verification_reading(self, access: VerificationAccess) -> AccountReading:
        try:
            state = self.read_state(Credentials(access.account_address, access.secret_key))
        except ExchangeRejectedCredentialsError as error:
            raise VerificationCredentialsRejectedError from error
        except ExchangeUnavailableError as error:
            raise VerificationExchangeUnavailableError from error
        return AccountReading(
            state.balance.amount,
            state.available_margin.amount,
            state.balance.currency,
            tuple(PositionReading(p.coin, p.side.value, p.size, p.leverage) for p in state.positions),
        )

    def cycle_reading(self, access: CycleAccess) -> CycleAccount:
        try:
            state = self.read_state(Credentials(access.account_address, access.secret_key))
        except ExchangeRejectedCredentialsError as error:
            raise FlowCredentialsRefusedError from error
        except ExchangeUnavailableError as error:
            raise FlowExchangeUnavailableError from error
        return CycleAccount(
            state.balance.currency,
            state.available_margin.amount,
            tuple(
                CyclePosition(
                    p.coin,
                    TradeSide(p.side.value),
                    p.size,
                    p.leverage,
                    p.entry_price,
                    p.unrealized_pnl,
                    p.liquidation_price,
                )
                for p in state.positions
            ),
        )

    def _traded_positions(self, credentials: Credentials) -> tuple[Position, ...]:
        if self._orders is None:
            return ()
        held = [p for (address, _), p in self._orders.positions.items() if address == credentials.account_address]
        return tuple(
            Position(
                p.coin,
                PositionSide(p.direction.value),
                p.size,
                p.leverage,
                self._orders.markets[p.coin].mid_price,
                Decimal(0),
                None,
            )
            for p in held
        )
