from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.accounts.register_account import AccountRegistration, RegisterAccountCommand


class AccountRegistrationRequest(BaseModel):
    # Missing values arrive empty, so the domain answers with the reason the requirement names (R0.2.1).
    name: str = ""
    exchange: str = ""
    account_address: str = ""
    secret_key: str = ""

    def __repr_args__(self) -> list[tuple[str | None, object]]:
        return [("name", self.name), ("exchange", self.exchange)]


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


def accounts_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/accounts", tags=["conti"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    def register_account(
        request: AccountRegistrationRequest, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> AccountRegistrationResponse:
        command = RegisterAccountCommand(request.name, request.exchange, request.account_address, request.secret_key)
        return AccountRegistrationResponse.of(use_cases.register_account.execute(command))

    return router
