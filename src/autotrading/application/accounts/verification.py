import logging
from collections.abc import Mapping

from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError, UnsupportedExchangeError
from autotrading.application.accounts.ports import ExchangePort
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.exchange_name import ExchangeName

# Operations on accounts are recorded by account id; the credentials never enter a record (R0.2.3).
operations = logging.getLogger("autotrading.accounts")


def supported_exchange(exchanges: Mapping[str, ExchangePort], exchange_name: ExchangeName) -> ExchangePort:
    exchange = exchanges.get(exchange_name.value)
    if exchange is None:
        raise UnsupportedExchangeError(exchange_name, exchanges)
    return exchange


def read_state_proving(exchange: ExchangePort, credentials: Credentials) -> AccountState:
    """Reads the state with these credentials; a refusal keeps the text of the exchange, redacted."""
    try:
        return exchange.read_state(credentials)
    except ExchangeRejectedCredentialsError as error:
        # No chained cause: the original exception still holds the text before redaction.
        raise ExchangeRejectedCredentialsError(credentials.redact(error.exchange_message)) from None
