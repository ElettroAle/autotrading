from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError, ExchangeUnavailableError
from autotrading.application.flows.errors import FlowCredentialsRefusedError, FlowExchangeUnavailableError
from autotrading.application.verification.errors import (
    VerificationCredentialsRejectedError,
    VerificationExchangeUnavailableError,
)
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credential_field import CredentialField
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.flows.cycle_access import CycleAccess
from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.verification.reading import AccountReading, PositionReading
from autotrading.domain.verification.verification_access import VerificationAccess
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.support.credentials import HYPERLIQUID_FIELDS

# What the user reads of a refusal: the text of the exchange with the address masked (R0.2.3).
REDACTED_REJECTION = "User or API Wallet *** does not exist."
# What the exchange says with a limit of frequency: the code in the cause, not this text, decides it is transient.
RATE_LIMITED_MESSAGE = "too many requests"
READ_AT = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


class TooManyRequestsResponse(Exception):  # noqa: N818 - the error the library of the exchange raises, not a project error
    """What the library of the exchange raises for a limit of frequency: the code the base error reads in the cause
    (ADR permanenza-decisa-dall-errore-base).
    """

    status_code = 429

    def __init__(self) -> None:
        super().__init__("429 too many requests")


def rejection_message(credentials: Credentials) -> str:
    """Hyperliquid names the wallet it does not know: the text of a refusal carries the address sent."""
    return f"User or API Wallet {credentials.value('account_address').upper()} does not exist."


class FakeExchangeAdapter:
    """An exchange that knows which credentials it accepts and the state of each account behind them."""

    def __init__(self, *, real: bool = False, network_name: str | None = None) -> None:
        self._real = real
        self._network_name = network_name or ("mainnet" if real else "testnet")
        self.fields: tuple[CredentialField, ...] = HYPERLIQUID_FIELDS
        self._states: dict[Credentials, AccountState] = {}
        self.reachable = True
        self.requests: list[Credentials] = []
        self.shown: dict[Credentials, list[AccountState]] = {}
        self._orders: FakeOrderExchangeAdapter | None = None
        self.refusal: ExchangeRejectedCredentialsError | None = None
        self._refusal_reasons: dict[Credentials, str] = {}
        self._rate_limited: set[Credentials] = set()
        # Whether the exchange tells until when credentials work, and the day it tells for each (R6.2.2).
        self.reads_expiry = False
        self.expiries: dict[Credentials, date] = {}
        self.expiry_refusal: ExchangeRejectedCredentialsError | None = None

    def is_real(self) -> bool:
        return self._real

    def network_name(self) -> str:
        return self._network_name

    def credential_fields(self) -> tuple[CredentialField, ...]:
        return self.fields

    def trades_on(self, orders: FakeOrderExchangeAdapter) -> None:
        """The same exchange for orders: the positions it holds for an account are part of its state."""
        self._orders = orders

    def accept(self, credentials: Credentials, amount: Decimal = Decimal("1000.00")) -> None:
        balance = Balance(amount, "USDC")
        self._states[credentials] = AccountState(balance, balance, (), READ_AT)
        self._refusal_reasons.pop(credentials, None)

    def open_position(self, credentials: Credentials, position: Position) -> None:
        state = self._states[credentials]
        self._states[credentials] = AccountState(
            state.balance, state.available_margin, (*state.positions, position), state.read_at
        )

    def set_available_margin(self, credentials: Credentials, amount: Decimal) -> None:
        state = self._states[credentials]
        self._states[credentials] = replace(state, available_margin=Balance(amount, state.balance.currency))

    def revoke(self, credentials: Credentials, reason: str | None = None) -> None:
        """The key is deleted or expired on the exchange: from now on it is refused, with the reason given if any."""
        self._states.pop(credentials, None)
        if reason is not None:
            self._refusal_reasons[credentials] = reason

    def limit_rate(self, credentials: Credentials) -> None:
        """The exchange answers too many requests to every reading of the account, as its library raises it."""
        self._rate_limited.add(credentials)

    def read_state(self, credentials: Credentials) -> AccountState:
        self.requests.append(credentials)
        if not self.reachable:
            raise ExchangeUnavailableError
        if self.refusal is not None:
            raise self.refusal
        if credentials in self._rate_limited:
            raise ExchangeRejectedCredentialsError(RATE_LIMITED_MESSAGE) from TooManyRequestsResponse()
        state = self._states.get(credentials)
        if state is None:
            reason = self._refusal_reasons.get(credentials, rejection_message(credentials))
            raise ExchangeRejectedCredentialsError(reason)
        shown = replace(state, positions=(*state.positions, *self._traded_positions(credentials)))
        self.shown.setdefault(credentials, []).append(shown)
        return shown

    def reads_credential_expiry(self) -> bool:
        return self.reads_expiry

    def credential_expiry(self, credentials: Credentials) -> date | None:
        if not self.reachable:
            raise ExchangeUnavailableError
        if self.expiry_refusal is not None:
            raise self.expiry_refusal
        return self.expiries.get(credentials)

    def valid_until(self, credentials: Credentials, expires_on: date) -> None:
        """The exchange tells the day the credentials stop working, as Hyperliquid does for an API wallet."""
        self.reads_expiry = True
        self.expiries[credentials] = expires_on

    def verification_reading(self, access: VerificationAccess) -> AccountReading:
        try:
            state = self.read_state(Credentials(access.fields))
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
            state = self.read_state(Credentials(access.fields))
        except ExchangeRejectedCredentialsError as error:
            raise FlowCredentialsRefusedError(error.exchange_message) from error
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
                    p.mark_price,
                    p.unrealized_pnl,
                    p.liquidation_price,
                )
                for p in state.positions
            ),
        )

    def _traded_positions(self, credentials: Credentials) -> tuple[Position, ...]:
        if self._orders is None:
            return ()
        held = [
            p for (address, _), p in self._orders.positions.items() if address == credentials.value("account_address")
        ]
        return tuple(
            Position(
                p.coin,
                PositionSide(p.direction.value),
                p.size,
                p.leverage,
                self._orders.markets[p.coin].mid_price,
                self._orders.markets[p.coin].mid_price,
                Decimal(0),
                None,
            )
            for p in held
        )
