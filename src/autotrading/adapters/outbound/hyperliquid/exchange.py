import secrets
from collections.abc import Mapping
from decimal import Decimal
from typing import cast

import requests
from eth_account import Account as EthereumAccount
from eth_account.signers.local import LocalAccount
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError
from hyperliquid.utils.types import Cloid

from autotrading.adapters.outbound.hyperliquid.user_state import _UserPosition, in_account_mode, user_state_of
from autotrading.application.accounts.errors import (
    CredentialFieldMalformedError,
    ExchangeRejectedCredentialsError,
    ExchangeUnavailableError,
)
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
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.verification.reading import AccountReading, PositionReading
from autotrading.domain.verification.verification_access import VerificationAccess

# The exchange refuses any order below 10 USDC of value ("Order must have minimum value of $10").
MIN_ORDER_VALUE = Decimal(10)
TIMEOUT_SECONDS = 10.0
# The SDK raises the same error for every 4xx; a limit of frequency passes by itself, so it is no refusal and pauses no
# flow (ADR limite-di-frequenza-dell-exchange-come-indisponibilita).
RATE_LIMITED_STATUS = 429
PROBE_COIN = "BTC"
MARGIN_CURRENCY = "USDC"
INVALID_KEY_MESSAGE = "chiave dell'API wallet non valida"
MISSING_FIELD_MESSAGE = "credenziali del conto incomplete"
# The shapes of the two fields: a value of another shape is refused before reaching the exchange, saying what is wrong
# in it and never a character of it (Bug 387).
HEX_PREFIX = "0x"
HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
KEY_DIGITS = 64
ADDRESS_DIGITS = 40
KEY_SHAPE = "attese 64 cifre esadecimali, con o senza 0x"
INVALID_ADDRESS_MESSAGE = "indirizzo del conto non valido"
ADDRESS_SHAPE = "atteso 0x seguito da 40 cifre esadecimali"
# A signature proves the key, not the account: the exchange applies an action of an API wallet to the account that
# approved it, whatever address the request names. The role of the signer ties it to the address (Bug 399).
AGENT_ROLE = "agent"
AGENT_NOT_AUTHORIZED_MESSAGE = "l'API wallet non è autorizzato per l'indirizzo del conto"
SIGNER_IS_AGENT_MESSAGE = (
    "l'indirizzo del conto è quello dell'API wallet: va indicato l'indirizzo del conto che lo ha approvato"
)
# The exchanges an account declares at registration: the use cases pick the adapter by this name (R2.3.11).
EXCHANGE_NAME = "Hyperliquid"
TESTNET_EXCHANGE_NAME = "Hyperliquid Testnet"
# The names Hyperliquid gives its networks (R2.3.10).
TESTNET = "testnet"
MAINNET = "mainnet"
# The names match the keys of the credentials already sealed, so nothing saved needs migrating (ADR 0158).
ACCOUNT_ADDRESS = "account_address"
API_WALLET_KEY = "secret_key"
CREDENTIAL_FIELDS = (
    CredentialField(ACCOUNT_ADDRESS, "Indirizzo del conto", secret=False),
    CredentialField(API_WALLET_KEY, "Chiave dell'API wallet", secret=True),
)


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
        self,
        base_url: str = MAINNET_API_URL,
        sdk: HyperliquidSdkAdapter | None = None,
        timeout: float = TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url
        self._sdk = sdk or HyperliquidSdkAdapter()
        self._timeout = timeout

    @property
    def base_url(self) -> str:
        return self._base_url

    def is_real(self) -> bool:
        return True

    def network_name(self) -> str:
        return MAINNET

    def credential_fields(self) -> tuple[CredentialField, ...]:
        return CREDENTIAL_FIELDS

    def read_state(self, credentials: Credentials) -> AccountState:
        address = _address_of(credentials)
        wallet = _wallet_of(credentials)
        try:
            exchange = self._sdk.exchange(wallet, self._base_url, address, self._timeout)
            _require_accepted(exchange.cancel_by_cloid(PROBE_COIN, _unused_cloid()), credentials)
            info = self._sdk.info(self._base_url, self._timeout)
            _require_signer_of(info.user_role(wallet.address), wallet.address, address)
            perps = info.user_state(address)
            mode = info.query_user_abstraction_state(address)
            spot = info.spot_user_state(address)
        except ClientError as error:
            _require_not_rate_limited(error)
            raise ExchangeRejectedCredentialsError(_masked(str(error.error_message), credentials)) from error
        except (ServerError, requests.RequestException) as error:
            raise ExchangeUnavailableError from error
        return _account_state_of(perps, mode, spot)

    def verification_reading(self, access: VerificationAccess) -> AccountReading:
        """The same reading for the verification procedure, which keeps only the reason of a failure (ADR 0024)."""
        try:
            state = self.read_state(Credentials(access.fields))
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

    def cycle_reading(self, access: CycleAccess) -> CycleAccount:
        """The same reading for the cycle of a flow: a refusal pauses the flows of the account (R1.2.4)."""
        try:
            state = self.read_state(Credentials(access.fields))
        except ExchangeRejectedCredentialsError as error:
            raise FlowCredentialsRefusedError from error
        except ExchangeUnavailableError as error:
            raise FlowExchangeUnavailableError from error
        return CycleAccount(
            currency=state.balance.currency,
            available_margin=state.available_margin.amount,
            positions=tuple(
                CyclePosition(
                    position.coin,
                    TradeSide(position.side.value),
                    position.size,
                    position.leverage,
                    position.entry_price,
                    position.mark_price,
                    position.unrealized_pnl,
                    position.liquidation_price,
                )
                for position in state.positions
            ),
        )


class HyperliquidTestnetExchangeAdapter(HyperliquidExchangeAdapter):
    """Hyperliquid Testnet, an exchange of its own an account can choose: the same exchange on the network of test,
    without real money (R2.3.11, ADR hyperliquid-testnet-come-adapter-dedicato)."""

    def __init__(self, sdk: HyperliquidSdkAdapter | None = None, timeout: float = TIMEOUT_SECONDS) -> None:
        super().__init__(TESTNET_API_URL, sdk, timeout)

    def is_real(self) -> bool:
        return False

    def network_name(self) -> str:
        return TESTNET


def _field(credentials: Credentials, name: str) -> str:
    """A field the exchange needs; credentials without it are refused as the exchange would refuse them."""
    found = credentials.values.get(name)
    if found is None:
        raise ExchangeRejectedCredentialsError(MISSING_FIELD_MESSAGE)
    return found


def _address_of(credentials: Credentials) -> str:
    address = _field(credentials, ACCOUNT_ADDRESS)
    if not address.startswith(HEX_PREFIX) or not _hexadecimal(address.removeprefix(HEX_PREFIX), ADDRESS_DIGITS):
        raise CredentialFieldMalformedError(
            ACCOUNT_ADDRESS, f"{INVALID_ADDRESS_MESSAGE}: {ADDRESS_SHAPE}; {_shape_of(address)}"
        )
    return address


def _wallet_of(credentials: Credentials) -> LocalAccount:
    key = _field(credentials, API_WALLET_KEY)
    if not _hexadecimal(_digits_of(key), KEY_DIGITS):
        raise CredentialFieldMalformedError(API_WALLET_KEY, f"{INVALID_KEY_MESSAGE}: {KEY_SHAPE}; {_shape_of(key)}")
    try:
        wallet: LocalAccount = EthereumAccount.from_key(key)
    except ValueError as error:
        # 64 hexadecimal digits that are no key of the curve, as zero.
        raise CredentialFieldMalformedError(API_WALLET_KEY, INVALID_KEY_MESSAGE) from error
    return wallet


def _digits_of(value: str) -> str:
    return value[len(HEX_PREFIX) :] if value[: len(HEX_PREFIX)].lower() == HEX_PREFIX else value


def _hexadecimal(digits: str, length: int) -> bool:
    return len(digits) == length and set(digits) <= HEX_DIGITS


def _shape_of(value: str) -> str:
    """What is wrong in a value, told without any of its characters: its length and how many are no hex digits."""
    foreign = sum(1 for character in _digits_of(value) if character not in HEX_DIGITS)
    received = f"ricevuti {len(value)} caratteri"
    return f"{received}, di cui {foreign} non esadecimali" if foreign else received


def _unused_cloid() -> Cloid:
    # Random 128 bits: it cannot match a client order id the platform assigned, so nothing is ever cancelled.
    return Cloid.from_int(secrets.randbits(128))


def _require_not_rate_limited(error: ClientError) -> None:
    if error.status_code == RATE_LIMITED_STATUS:
        raise ExchangeUnavailableError from error


def _require_accepted(response: object, credentials: Credentials) -> None:
    if isinstance(response, Mapping) and response.get("status") == "ok":
        return
    message = response.get("response") if isinstance(response, Mapping) else response
    raise ExchangeRejectedCredentialsError(_masked(str(message), credentials))


def _require_signer_of(role: object, signer: str, address: str) -> None:
    # The account signs for itself only if it is no API wallet; an API wallet signs only for the account it serves.
    try:
        answer = cast("Mapping[str, object]", role)
        declared = answer["role"]
        served = cast("Mapping[str, object]", answer["data"])["user"] if declared == AGENT_ROLE else None
    except (KeyError, TypeError) as error:
        raise ExchangeUnavailableError from error
    if signer.lower() == address.lower():
        _require_not_agent(declared)
        return
    if not isinstance(served, str) or served.lower() != address.lower():
        raise ExchangeRejectedCredentialsError(AGENT_NOT_AUTHORIZED_MESSAGE)


def _require_not_agent(declared: object) -> None:
    if declared == AGENT_ROLE:
        raise ExchangeRejectedCredentialsError(SIGNER_IS_AGENT_MESSAGE)


def _account_state_of(perps: object, mode: object, spot: object) -> AccountState:
    # An answer of unexpected shape is a fault of the exchange, never a reason to report invented values.
    try:
        read = in_account_mode(user_state_of(perps), mode, spot)
    except (KeyError, TypeError, ValueError, ArithmeticError) as error:
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
        mark_price=position.mark_price,
        unrealized_pnl=position.unrealized_pnl,
        liquidation_price=position.liquidation_price,
    )


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _masked(message: str, credentials: Credentials) -> str:
    # The message of the exchange goes back to the user; the credentials it may echo never do (R0.2.3).
    return credentials.redact(message)
