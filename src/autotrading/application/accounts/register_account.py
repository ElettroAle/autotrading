from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from autotrading.application.accounts.errors import AccountNameInUseError, VirtualBalanceNotHeldError
from autotrading.application.accounts.ports import (
    AccountRepositoryPort,
    CredentialSealerPort,
    ExchangePort,
    VirtualBalancePort,
)
from autotrading.application.accounts.verification import (
    expiry_at_check,
    operations,
    read_state_proving,
    supported_exchange,
)
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.accounts.virtual_balance import VirtualBalance
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class RegisterAccountCommand:
    name: str
    exchange: str
    credentials: Mapping[str, str] = field(repr=False)
    # The day the credentials stop working, given only for an exchange that does not read it (R6.2.2).
    expires_on: date | None = None
    # The balance an account starts from, given only for an exchange that holds a virtual one (R6.3.2).
    virtual_balance: Decimal | None = None


@dataclass(frozen=True, slots=True)
class RegistrationPorts:
    """Where the account is saved, what seals its credentials, the exchanges it can be on, and those of them that hold
    a virtual balance instead of funds (R6.3.2).
    """

    accounts: AccountRepositoryPort
    sealer: CredentialSealerPort
    exchanges: Mapping[str, ExchangePort]
    virtual_balances: Mapping[str, VirtualBalancePort]


@dataclass(frozen=True, slots=True)
class AccountRegistration:
    account: Account
    balance: Balance


class RegisterAccountUseCase:
    """Saves an account in the tenant after the exchange has accepted its credentials (R0.2.1), with the expiry the
    exchange reads for them or the one the user gave (R6.2.2).

    An exchange that declares no credential field has none to accept or seal; one that holds a virtual balance opens
    the account on the balance the user gives before its state is read (R6.3.2).
    """

    def __init__(self, tenant_id: TenantId, ports: RegistrationPorts) -> None:
        self._tenant_id = tenant_id
        self._ports = ports

    def execute(self, command: RegisterAccountCommand) -> AccountRegistration:
        name = AccountName(command.name)
        exchange_name = ExchangeName(command.exchange)
        exchange = supported_exchange(self._ports.exchanges, exchange_name)
        fields = exchange.credential_fields()
        account_id = AccountId.new()
        credentials = Credentials.for_account(account_id, fields, command.credentials)
        self._require_free(name)
        self._open_virtual_balance(exchange_name, account_id, command.virtual_balance)
        balance = read_state_proving(exchange, credentials).balance
        expiry = expiry_at_check(exchange, credentials, command.expires_on)
        exchange_account = ExchangeAccount.of(credentials, fields)
        account = Account(
            account_id, self._tenant_id, name, exchange_name, exchange_account, self._sealed(account_id, credentials)
        ).with_expiry(expiry)
        self._ports.accounts.add(account)
        operations.info("conto registrato", extra={"account_id": str(account.id.value)})
        return AccountRegistration(account, balance)

    def _require_free(self, name: AccountName) -> None:
        if self._ports.accounts.name_in_use(name):
            raise AccountNameInUseError(name)

    def _open_virtual_balance(self, exchange: ExchangeName, account_id: AccountId, amount: Decimal | None) -> None:
        virtual_balances = self._ports.virtual_balances.get(exchange.value)
        if virtual_balances is None and amount is not None:
            raise VirtualBalanceNotHeldError
        if virtual_balances is None:
            return
        virtual_balances.open(account_id, VirtualBalance.required(amount))

    def _sealed(self, account_id: AccountId, credentials: Credentials) -> SealedCredentials:
        """Nothing to seal for an exchange without credentials (R6.3.2)."""
        if credentials.is_empty:
            return SealedCredentials.none()
        return self._ports.sealer.seal(account_id, credentials)
