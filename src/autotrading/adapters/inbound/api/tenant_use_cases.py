from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.application.accounts.get_account import GetAccountUseCase
from autotrading.application.accounts.list_accounts import ListAccountsUseCase
from autotrading.application.accounts.ports import (
    AccountRepositoryPort,
    AccountStatePort,
    CredentialSealerPort,
    ExchangePort,
)
from autotrading.application.accounts.read_account_state import ReadAccountStateUseCase
from autotrading.application.accounts.register_account import RegisterAccountUseCase
from autotrading.application.accounts.replace_credentials import ReplaceCredentialsUseCase
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class TenantUseCases:
    """The use cases of one request, built by bootstrap.for_tenant on adapters bound to the tenant of the request."""

    register_account: RegisterAccountUseCase
    list_accounts: ListAccountsUseCase
    get_account: GetAccountUseCase
    replace_credentials: ReplaceCredentialsUseCase
    read_account_state: ReadAccountStateUseCase

    @classmethod
    def on(
        cls,
        tenant_id: TenantId,
        accounts: AccountRepositoryPort,
        sealer: CredentialSealerPort,
        exchanges: Mapping[str, ExchangePort],
        account_state: AccountStatePort,
    ) -> TenantUseCases:
        return cls(
            register_account=RegisterAccountUseCase(tenant_id, accounts, sealer, exchanges),
            list_accounts=ListAccountsUseCase(accounts),
            get_account=GetAccountUseCase(accounts),
            replace_credentials=ReplaceCredentialsUseCase(accounts, sealer, exchanges),
            read_account_state=ReadAccountStateUseCase(accounts, account_state),
        )
