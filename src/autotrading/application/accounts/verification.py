import logging

from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError
from autotrading.application.accounts.ports import ExchangePort
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credentials import Credentials

# Operations on accounts are recorded by account id; the credentials never enter a record (R0.2.3).
operations = logging.getLogger("autotrading.accounts")


def read_balance_proving(exchange: ExchangePort, credentials: Credentials) -> Balance:
    """Reads the balance with the credentials of the request; a refusal keeps the exchange text, redacted."""
    try:
        return exchange.read_balance(credentials)
    except ExchangeRejectedCredentialsError as error:
        # No chained cause: the original exception still holds the text before redaction.
        raise ExchangeRejectedCredentialsError(credentials.redact(error.exchange_message)) from None
