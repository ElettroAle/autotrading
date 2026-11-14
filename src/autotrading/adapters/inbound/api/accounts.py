from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from autotrading.adapters.inbound.api.account_state import AccountStateResponse
from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.accounts.account_details import AccountDetails
from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.get_account import GetAccountCommand
from autotrading.application.accounts.read_account_state import ReadAccountStateCommand
from autotrading.application.accounts.register_account import AccountRegistration, RegisterAccountCommand
from autotrading.application.accounts.replace_credentials import ReplaceCredentialsCommand
from autotrading.application.flows.remove_account_with_flows import RemoveAccountWithFlowsCommand
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.tenancy.user_id import UserId


class AccountRegistrationRequest(BaseModel):
    # Missing values arrive empty, so the domain answers with the reason the requirement names (R0.2.1).
    name: str = ""
    exchange: str = ""
    account_address: str = ""
    secret_key: str = ""

    def __repr_args__(self) -> list[tuple[str | None, object]]:
        return [("name", self.name), ("exchange", self.exchange)]


class CredentialsReplacementRequest(BaseModel):
    account_address: str = ""
    secret_key: str = ""

    def __repr_args__(self) -> list[tuple[str | None, object]]:
        return []


class AccountDetailsResponse(BaseModel):
    """An account as its owner reads it: credentials are only declared present, never returned (R0.2.3)."""

    id: str
    name: str
    exchange: str
    has_credentials: bool

    @classmethod
    def of(cls, details: AccountDetails) -> AccountDetailsResponse:
        return cls(
            id=str(details.id.value),
            name=details.name.value,
            exchange=details.exchange.value,
            has_credentials=details.has_credentials,
        )


class AccountSummaryResponse(AccountDetailsResponse):
    """An account in the list of its owner (R2.2.1, ADR 0126): network and capital its flows hold, never the balance,
    which the exchange gives at /accounts/{id}/state."""

    network: str
    allocated_capital: str
    currency: str

    @classmethod
    def of_summary(cls, summary: AccountSummary) -> AccountSummaryResponse:
        return cls(
            id=str(summary.id.value),
            name=summary.name.value,
            exchange=summary.exchange.value,
            has_credentials=summary.has_credentials,
            network=summary.network.value,
            allocated_capital=amount_text(summary.allocated_capital),
            currency=summary.currency,
        )


class BalanceResponse(BaseModel):
    amount: str
    currency: str


class AccountRegistrationResponse(BaseModel):
    id: str
    name: str
    exchange: str
    balance: BalanceResponse

    @classmethod
    def of(cls, registration: AccountRegistration) -> AccountRegistrationResponse:
        account = registration.account
        return cls(
            id=str(account.id.value),
            name=account.name.value,
            exchange=account.exchange.value,
            balance=BalanceResponse(amount=str(registration.balance.amount), currency=registration.balance.currency),
        )


def accounts_router(
    use_cases_of_request: Callable[..., TenantUseCases], user_of_request: Callable[..., UserId]
) -> APIRouter:
    router = APIRouter(prefix="/accounts", tags=["conti"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    def register_account(
        request: AccountRegistrationRequest, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> AccountRegistrationResponse:
        command = RegisterAccountCommand(request.name, request.exchange, request.account_address, request.secret_key)
        return AccountRegistrationResponse.of(use_cases.register_account.execute(command))

    @router.get("")
    def list_accounts(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> list[AccountSummaryResponse]:
        return [AccountSummaryResponse.of_summary(summary) for summary in use_cases.list_accounts.execute()]

    @router.get("/{account_id}")
    def get_account(
        account_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> AccountSummaryResponse:
        command = GetAccountCommand(AccountId(account_id))
        return AccountSummaryResponse.of_summary(use_cases.get_account.execute(command))

    @router.put("/{account_id}/credentials")
    def replace_credentials(
        account_id: UUID,
        request: CredentialsReplacementRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> AccountDetailsResponse:
        command = ReplaceCredentialsCommand(AccountId(account_id), request.account_address, request.secret_key)
        return AccountDetailsResponse.of(use_cases.replace_credentials.execute(command))

    @router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
    def remove_account(
        account_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        user_id: Annotated[UserId, Depends(user_of_request)],
        confirmed: bool = False,
    ) -> None:
        # Without confirmation an account with flows operating or open positions is kept (R0.2.5, R1.1.8).
        command = RemoveAccountWithFlowsCommand(account_id, user_id, confirmed=confirmed)
        use_cases.remove_account_with_flows.execute(command)

    @router.get("/{account_id}/state")
    def read_account_state(
        account_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> AccountStateResponse:
        command = ReadAccountStateCommand(AccountId(account_id))
        return AccountStateResponse.of(use_cases.read_account_state.execute(command))

    return router
