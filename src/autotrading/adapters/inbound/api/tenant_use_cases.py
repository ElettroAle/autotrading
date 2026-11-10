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
from autotrading.application.orders.close_position import ClosePositionUseCase
from autotrading.application.orders.ports import PositionClosingPort
from autotrading.application.verification.ports import VerificationPort
from autotrading.application.verification.run_verification import RunVerificationUseCase
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class TenantPorts:
    """The adapters of one request, bound to its tenant, that the use cases of the API run on."""

    accounts: AccountRepositoryPort
    sealer: CredentialSealerPort
    exchanges: Mapping[str, ExchangePort]
    account_state: AccountStatePort
    position_closing: PositionClosingPort
    verification: VerificationPort


@dataclass(frozen=True, slots=True)
class TenantUseCases:
    """The use cases of one request, built by bootstrap.for_tenant on adapters bound to the tenant of the request."""

    register_account: RegisterAccountUseCase
    list_accounts: ListAccountsUseCase
    get_account: GetAccountUseCase
    replace_credentials: ReplaceCredentialsUseCase
    read_account_state: ReadAccountStateUseCase
    close_position: ClosePositionUseCase
    run_verification: RunVerificationUseCase

    @classmethod
    def on(cls, tenant_id: TenantId, ports: TenantPorts) -> TenantUseCases:
        accounts, sealer, exchanges = ports.accounts, ports.sealer, ports.exchanges
        return cls(
            register_account=RegisterAccountUseCase(tenant_id, accounts, sealer, exchanges),
            list_accounts=ListAccountsUseCase(accounts),
            get_account=GetAccountUseCase(accounts),
            replace_credentials=ReplaceCredentialsUseCase(accounts, sealer, exchanges),
            read_account_state=ReadAccountStateUseCase(accounts, ports.account_state),
            close_position=ClosePositionUseCase(ports.position_closing),
            run_verification=RunVerificationUseCase(ports.verification),
        )
