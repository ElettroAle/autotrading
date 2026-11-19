import logging
from collections.abc import Mapping
from datetime import date

from autotrading.application.accounts.errors import (
    ExchangeRejectedCredentialsError,
    KeyExpiryReadByAdapterError,
    UnsupportedExchangeError,
)
from autotrading.application.accounts.ports import ExchangePort
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.declared_network import DeclaredNetwork
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.key_expiry import KeyExpiry

# Operations on accounts are recorded by account id; the credentials never enter a record (R0.2.3).
operations = logging.getLogger("autotrading.accounts")


def supported_exchange(exchanges: Mapping[str, ExchangePort], exchange_name: ExchangeName) -> ExchangePort:
    exchange = exchanges.get(exchange_name.value)
    if exchange is None:
        raise UnsupportedExchangeError(exchange_name, exchanges)
    return exchange


def network_of(exchanges: Mapping[str, ExchangePort], exchange_name: ExchangeName) -> DeclaredNetwork:
    """The network the adapter of the exchange is configured on, never the name of the installation (Bug 277), with the
    name the exchange gives it (R2.3.10)."""
    exchange = supported_exchange(exchanges, exchange_name)
    return DeclaredNetwork.of(real=exchange.is_real(), name=exchange.network_name())


def read_state_proving(exchange: ExchangePort, credentials: Credentials) -> AccountState:
    """Reads the state with these credentials; a refusal keeps the text of the exchange, redacted."""
    try:
        return exchange.read_state(credentials)
    except ExchangeRejectedCredentialsError as error:
        # No chained cause: the original exception still holds the text before redaction.
        raise error.with_exchange_message(credentials.redact(error.exchange_message)) from None


def require_expiry_editable(exchange: ExchangePort) -> None:
    """The user gives the expiry only of credentials whose exchange does not read it (R6.2.2)."""
    if exchange.reads_credential_expiry():
        raise KeyExpiryReadByAdapterError


def expiry_at_check(exchange: ExchangePort, credentials: Credentials, entered: date | None) -> KeyExpiry | None:
    """The expiry of credentials being checked: the one the exchange reads, if it reads it, else the date the user
    gave, if any (R6.2.2, ADR scadenza-delle-chiavi-letta-o-indicata).
    """
    if entered is not None:
        require_expiry_editable(exchange)
        return KeyExpiry.entered(entered)
    if not exchange.reads_credential_expiry():
        return None
    return read_expiry_proving(exchange, credentials)


def read_expiry_proving(exchange: ExchangePort, credentials: Credentials) -> KeyExpiry | None:
    """The expiry the exchange tells for these credentials; a refusal keeps the text of the exchange, redacted."""
    try:
        expires_on = exchange.credential_expiry(credentials)
    except ExchangeRejectedCredentialsError as error:
        # No chained cause: the original exception still holds the text before redaction.
        raise error.with_exchange_message(credentials.redact(error.exchange_message)) from None
    return None if expires_on is None else KeyExpiry.read(expires_on)
