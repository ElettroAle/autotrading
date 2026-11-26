from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from autotrading.adapters.inbound.api.account_state import AccountStateResponse
from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.key_expiry import ExpiryStatus, KeyExpiryRequest, KeyExpiryResponse
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.accounts.account_details import AccountDetails
from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.get_account import GetAccountCommand
from autotrading.application.accounts.read_account_state import ReadAccountStateCommand
from autotrading.application.accounts.register_account import AccountRegistration, RegisterAccountCommand
from autotrading.application.accounts.replace_credentials import ReplaceCredentialsCommand
from autotrading.application.accounts.reset_virtual_balance import ResetVirtualBalanceCommand
from autotrading.application.accounts.set_account_key_expiry import SetAccountKeyExpiryCommand
from autotrading.application.accounts.set_max_direction_exposure import SetMaxDirectionExposureCommand
from autotrading.application.flows.remove_account_with_flows import RemoveAccountWithFlowsCommand
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.tenancy.user_id import UserId


class AccountRegistrationRequest(BaseModel):
    # Missing values arrive empty, so the domain answers with the reason the requirement names (R0.2.1).
    # The credentials hold the fields the exchange declares, by name (R2.3.9): the domain checks them.
    name: str = ""
    exchange: str = ""
    credentials: dict[str, str] = Field(default_factory=dict)
    # Only for an exchange that does not read the expiry of the credentials (R6.2.2).
    expires_on: date | None = None
    # Only for an exchange that holds a virtual balance: what the account starts from (R6.3.2).
    virtual_balance: Decimal | None = None

    def __repr_args__(self) -> list[tuple[str | None, object]]:
        return [("name", self.name), ("exchange", self.exchange)]


class VirtualBalanceResetRequest(BaseModel):
    """The balance an account of an exchange with a virtual balance starts again from (R6.3.2)."""

    balance: Decimal


class CredentialsReplacementRequest(BaseModel):
    credentials: dict[str, str] = Field(default_factory=dict)
    expires_on: date | None = None

    def __repr_args__(self) -> list[tuple[str | None, object]]:
        return []


class MaxDirectionExposureRequest(BaseModel):
    """The largest exposure the flows of the account may have together on one side, in percent of its balance read from
    the exchange; null takes it away (R5.5.5)."""

    percent: Decimal | None = None


class AccountDetailsResponse(BaseModel):
    """An account as its owner reads it: secret credentials are only declared present, never returned (R0.2.3); the
    public fields the exchange declares are shown by name (Bug 401)."""

    id: str
    name: str
    exchange: str
    has_credentials: bool
    public_fields: dict[str, str]

    @classmethod
    def of(cls, details: AccountDetails) -> AccountDetailsResponse:
        return cls(
            id=str(details.id.value),
            name=details.name.value,
            exchange=details.exchange.value,
            has_credentials=details.has_credentials,
            public_fields=dict(details.public_fields),
        )


class AccountSummaryResponse(AccountDetailsResponse):
    """An account in the list of its owner (R2.2.1, ADR 0126): network and capital its flows hold, never the balance,
    which the exchange gives at /accounts/{id}/state; the expiry of its credentials as of today, with its state
    (`unknown`, `valid`, `expiring` within 30 days, `expired`) and the days left, and whether the user may give it
    (R6.2.2); the largest exposure its flows may have together on one side, in percent of its balance, null without a
    limit (R5.5.5)."""

    network: str
    network_name: str
    allocated_capital: str
    currency: str
    expiry: KeyExpiryResponse | None
    expiry_status: ExpiryStatus
    days_left: int | None
    expiry_editable: bool
    max_direction_exposure_percent: str | None

    @classmethod
    def of_summary(cls, summary: AccountSummary) -> AccountSummaryResponse:
        return cls(
            id=str(summary.id.value),
            name=summary.name.value,
            exchange=summary.exchange.value,
            has_credentials=summary.has_credentials,
            public_fields=dict(summary.public_fields),
            network=summary.network.kind.value,
            network_name=summary.network.name,
            allocated_capital=amount_text(summary.allocated_capital),
            currency=summary.currency,
            expiry=_expiry_response_of(summary),
            expiry_status=ExpiryStatus(summary.expiry.reading.status.value),
            days_left=summary.expiry.reading.days_left,
            expiry_editable=summary.expiry.editable,
            max_direction_exposure_percent=_percent_text(summary.max_direction_exposure_percent),
        )


def _expiry_response_of(summary: AccountSummary) -> KeyExpiryResponse | None:
    expiry = summary.expiry.expiry
    return None if expiry is None else KeyExpiryResponse.of(expiry.expires_on, expiry.source)


def _percent_text(percent: Decimal | None) -> str | None:
    return None if percent is None else amount_text(percent)


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
        command = RegisterAccountCommand(
            request.name, request.exchange, request.credentials, request.expires_on, request.virtual_balance
        )
        return AccountRegistrationResponse.of(use_cases.register_account.execute(command))

    @router.put("/{account_id}/virtual-balance", status_code=status.HTTP_204_NO_CONTENT)
    def reset_virtual_balance(
        account_id: UUID,
        request: VirtualBalanceResetRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> None:
        """Starts the account again from the balance given, its positions closed and its orders cancelled, on an
        exchange that holds a virtual balance (R6.3.2)."""
        command = ResetVirtualBalanceCommand(AccountId(account_id), request.balance)
        use_cases.reset_virtual_balance.execute(command)

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
        command = ReplaceCredentialsCommand(AccountId(account_id), request.credentials, request.expires_on)
        return AccountDetailsResponse.of(use_cases.replace_credentials.execute(command))

    @router.put("/{account_id}/expiry", status_code=status.HTTP_204_NO_CONTENT)
    def set_key_expiry(
        account_id: UUID,
        request: KeyExpiryRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> None:
        """The day the user says the credentials stop working, only when the exchange does not read it (R6.2.2)."""
        command = SetAccountKeyExpiryCommand(AccountId(account_id), request.expires_on)
        use_cases.set_account_key_expiry.execute(command)

    @router.put("/{account_id}/max-direction-exposure", status_code=status.HTTP_204_NO_CONTENT)
    def set_max_direction_exposure(
        account_id: UUID,
        request: MaxDirectionExposureRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> None:
        """Sets or takes away the limit of the exposure of the flows of the account on one side (R5.5.5)."""
        command = SetMaxDirectionExposureCommand(AccountId(account_id), request.percent)
        use_cases.set_max_direction_exposure.execute(command)

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
