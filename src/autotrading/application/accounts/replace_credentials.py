from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date

from autotrading.application.accounts.account_details import AccountDetails
from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountRepositoryPort, CredentialSealerPort, ExchangePort
from autotrading.application.accounts.verification import (
    expiry_at_check,
    operations,
    read_state_proving,
    supported_exchange,
)
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.exchange_account import ExchangeAccount


@dataclass(frozen=True, slots=True)
class ReplaceCredentialsCommand:
    account_id: AccountId
    credentials: Mapping[str, str] = field(repr=False)
    # The day the new credentials stop working, given only for an exchange that does not read it (R6.2.2).
    expires_on: date | None = None


class ReplaceCredentialsUseCase:
    """Swaps the credentials of an account once the exchange accepts them; on any refusal the old stay (R0.2.4).

    The expiry of the old credentials goes with them: the new ones carry the date the exchange reads, or the one the
    user gave with them, or none (R6.2.2).
    """

    def __init__(
        self,
        accounts: AccountRepositoryPort,
        sealer: CredentialSealerPort,
        exchanges: Mapping[str, ExchangePort],
    ) -> None:
        self._accounts = accounts
        self._sealer = sealer
        self._exchanges = exchanges

    def execute(self, command: ReplaceCredentialsCommand) -> AccountDetails:
        account = find_account(self._accounts, command.account_id)
        exchange = supported_exchange(self._exchanges, account.exchange)
        fields = exchange.credential_fields()
        credentials = Credentials.replacing(fields, account.exchange_account.public_fields, command.credentials)
        confirmed = account.with_exchange_account(ExchangeAccount.of(credentials, fields))
        read_state_proving(exchange, credentials)
        expiry = expiry_at_check(exchange, credentials, command.expires_on)
        replaced = confirmed.with_credentials(self._sealer.seal(account.id, credentials)).with_expiry(expiry)
        self._accounts.replace(replaced)
        operations.info("credenziali sostituite", extra={"account_id": str(account.id.value)})
        return AccountDetails.of(replaced)
