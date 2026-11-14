"""Credentials of the only exchange, by the fields its adapter declares (R2.3.9, ADR 0158)."""

from autotrading.domain.accounts.credential_field import CredentialField
from autotrading.domain.accounts.credentials import Credentials

ACCOUNT_ADDRESS = "account_address"
API_WALLET_KEY = "secret_key"
ADDRESS_LABEL = "Indirizzo del conto"
API_WALLET_KEY_LABEL = "Chiave dell'API wallet"
HYPERLIQUID_FIELDS = (
    CredentialField(ACCOUNT_ADDRESS, ADDRESS_LABEL, secret=False),
    CredentialField(API_WALLET_KEY, API_WALLET_KEY_LABEL, secret=True),
)


def hyperliquid_credentials(account_address: str, secret_key: str) -> Credentials:
    return Credentials({ACCOUNT_ADDRESS: account_address, API_WALLET_KEY: secret_key})


def credentials_of(account_address: str, secret_key: str) -> dict[str, str]:
    """The values a request of registration sends, by the name of each field."""
    return {ACCOUNT_ADDRESS: account_address, API_WALLET_KEY: secret_key}
