import re
import secrets
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from eth_account import Account as EthereumAccount
from eth_account.signers.local import LocalAccount
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError
from hyperliquid.utils.types import Cloid

from autotrading.adapters.outbound.hyperliquid.user_state import _UserPosition, user_state_of
from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError, ExchangeUnavailableError
from autotrading.application.verification.errors import (
    VerificationCredentialsRejectedError,
    VerificationExchangeUnavailableError,
)
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.verification.reading import AccountReading, PositionReading
from autotrading.domain.verification.verification_access import VerificationAccess

# The exchange refuses any order below 10 USDC of value ("Order must have minimum value of $10").
MIN_ORDER_VALUE = Decimal(10)
TIMEOUT_SECONDS = 10.0
PROBE_COIN = "BTC"
MARGIN_CURRENCY = "USDC"
INVALID_KEY_MESSAGE = "chiave dell'API wallet non valida"
MASK = "***"


class HyperliquidSdkAdapter:
    """The official Hyperliquid SDK, the only client of the exchange (rule tech-hyperliquid).

    The adapters of the folder take it in their constructor; a test hands them a subclass that answers for the exchange.
    """

    def exchange(self, wallet: LocalAccount, base_url: str, account_address: str, timeout: float) -> Exchange:
        return Exchange(wallet, base_url, account_address=account_address, timeout=timeout)

    def info(self, base_url: str, timeout: float) -> Info:
        return Info(base_url, skip_ws=True, timeout=timeout)


class HyperliquidExchangeAdapter:
    """Proves the credentials with a signed cancel of an order that cannot exist, then reads the account state.

    The cancel changes nothing on the exchange, but only a signer approved for the account gets an answer other than
    the rejection of the exchange, whose message is kept (R0.2.1, ADR 0018). No retries, 10 seconds of timeout.
    """

    def __init__(
        self, base_url: str, sdk: HyperliquidSdkAdapter | None = None, timeout: float = TIMEOUT_SECONDS
    ) -> None:
        self._base_url = base_url
        self._sdk = sdk or HyperliquidSdkAdapter()
        self._timeout = timeout

    @property
    def base_url(self) -> str:
        return self._base_url

    @classmethod
    def for_network(cls, *, testnet: bool, sdk: HyperliquidSdkAdapter | None = None) -> HyperliquidExchangeAdapter:
        # The network is chosen by the installation, never deduced from the credentials.
        return cls(TESTNET_API_URL if testnet else MAINNET_API_URL, sdk)

    def read_state(self, credentials: Credentials) -> AccountState:
        wallet = _wallet_of(credentials)
        try:
            exchange = self._sdk.exchange(wallet, self._base_url, credentials.account_address, self._timeout)
            _require_accepted(exchange.cancel_by_cloid(PROBE_COIN, _unused_cloid()), credentials)
            state = self._sdk.info(self._base_url, self._timeout).user_state(credentials.account_address)
        except ClientError as error:
            raise ExchangeRejectedCredentialsError(_masked(str(error.error_message), credentials)) from error
        except (ServerError, requests.RequestException) as error:
            raise ExchangeUnavailableError from error
        return _account_state_of(state)

    def verification_reading(self, access: VerificationAccess) -> AccountReading:
        """The same reading for the verification procedure, which keeps only the reason of a failure (ADR 0024)."""
        try:
            state = self.read_state(Credentials(access.account_address, access.secret_key))
        except ExchangeRejectedCredentialsError as error:
            raise VerificationCredentialsRejectedError from error
        except ExchangeUnavailableError as error:
            raise VerificationExchangeUnavailableError from error
        return AccountReading(
            balance=state.balance.amount,
            available_margin=state.available_margin.amount,
            currency=state.balance.currency,
            positions=tuple(
                PositionReading(position.coin, position.side.value, position.size, position.leverage)
                for position in state.positions
            ),
        )


def _wallet_of(credentials: Credentials) -> LocalAccount:
    try:
        wallet: LocalAccount = EthereumAccount.from_key(credentials.secret_key)
    except ValueError as error:
        raise ExchangeRejectedCredentialsError(INVALID_KEY_MESSAGE) from error
    return wallet


def _unused_cloid() -> Cloid:
    # Random 128 bits: it cannot match a client order id the platform assigned, so nothing is ever cancelled.
    return Cloid.from_int(secrets.randbits(128))


def _require_accepted(response: Any, credentials: Credentials) -> None:
    if isinstance(response, Mapping) and response.get("status") == "ok":
        return
    message = response.get("response") if isinstance(response, Mapping) else response
    raise ExchangeRejectedCredentialsError(_masked(str(message), credentials))


def _account_state_of(state: Any) -> AccountState:
    # An answer of unexpected shape is a fault of the exchange, never a reason to report invented values.
    try:
        read = user_state_of(state)
    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
        raise ExchangeUnavailableError from error
    return AccountState(
        balance=Balance(read.account_value, MARGIN_CURRENCY),
        available_margin=Balance(read.withdrawable, MARGIN_CURRENCY),
        positions=tuple(_position_of(position) for position in read.positions),
        read_at=read.read_at,
    )


def _position_of(position: _UserPosition) -> Position:
    return Position(
        coin=position.coin,
        side=PositionSide.LONG if position.signed_size > 0 else PositionSide.SHORT,
        size=abs(position.signed_size),
        leverage=position.leverage,
        entry_price=position.entry_price,
        unrealized_pnl=position.unrealized_pnl,
        liquidation_price=position.liquidation_price,
    )


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _masked(message: str, credentials: Credentials) -> str:
    # The message of the exchange goes back to the user; the credentials it may echo never do (R0.2.3).
    for secret in (credentials.secret_key, credentials.account_address):
        message = re.sub(re.escape(secret), MASK, message, flags=re.IGNORECASE)
    return message
