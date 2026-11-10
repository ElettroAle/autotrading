from collections.abc import Mapping
from dataclasses import dataclass, field

from autotrading.application.accounts.errors import AccountNameInUseError
from autotrading.application.accounts.ports import AccountRepositoryPort, CredentialSealerPort, ExchangePort
from autotrading.application.accounts.verification import operations, read_state_proving, supported_exchange
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class RegisterAccountCommand:
    name: str
    exchange: str
    account_address: str = field(repr=False)
    secret_key: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class AccountRegistration:
    account: Account
    balance: Balance


class RegisterAccountUseCase:
    """Saves an account in the tenant after the exchange has accepted its credentials (R0.2.1)."""

    def __init__(
        self,
        tenant_id: TenantId,
        accounts: AccountRepositoryPort,
        sealer: CredentialSealerPort,
        exchanges: Mapping[str, ExchangePort],
    ) -> None:
        self._tenant_id = tenant_id
        self._accounts = accounts
        self._sealer = sealer
        self._exchanges = exchanges

    def execute(self, command: RegisterAccountCommand) -> AccountRegistration:
        name = AccountName(command.name)
        exchange_name = ExchangeName(command.exchange)
        credentials = Credentials(command.account_address, command.secret_key)
        exchange = supported_exchange(self._exchanges, exchange_name)
        self._require_free(name)
        balance = read_state_proving(exchange, credentials).balance
        account = self._sealed_account(name, exchange_name, credentials)
        self._accounts.add(account)
        operations.info("conto registrato", extra={"account_id": str(account.id.value)})
        return AccountRegistration(account, balance)

    def _require_free(self, name: AccountName) -> None:
        if self._accounts.name_in_use(name):
            raise AccountNameInUseError(name)

    def _sealed_account(self, name: AccountName, exchange: ExchangeName, credentials: Credentials) -> Account:
        account_id = AccountId.new()
        sealed = self._sealer.seal(account_id, credentials)
        return Account(account_id, self._tenant_id, name, exchange, ExchangeAccount.of(credentials), sealed)
