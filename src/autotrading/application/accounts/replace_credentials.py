from collections.abc import Mapping
from dataclasses import dataclass, field

from autotrading.application.accounts.account_details import AccountDetails
from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountRepositoryPort, CredentialSealerPort, ExchangePort
from autotrading.application.accounts.verification import operations, read_state_proving, supported_exchange
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.credentials import Credentials


@dataclass(frozen=True, slots=True)
class ReplaceCredentialsCommand:
    account_id: AccountId
    account_address: str = field(repr=False)
    secret_key: str = field(repr=False)


class ReplaceCredentialsUseCase:
    """Swaps the credentials of an account once the exchange accepts them; on any refusal the old stay (R0.2.4)."""

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
        credentials = Credentials(command.account_address, command.secret_key)
        account.require_same_exchange_account(credentials)
        read_state_proving(supported_exchange(self._exchanges, account.exchange), credentials)
        replaced = account.with_credentials(self._sealer.seal(account.id, credentials))
        self._accounts.replace(replaced)
        operations.info("credenziali sostituite", extra={"account_id": str(account.id.value)})
        return AccountDetails.of(replaced)
