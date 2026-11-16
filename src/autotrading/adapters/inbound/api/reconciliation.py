from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.accounts.set_deviation_threshold import SetDeviationThresholdCommand
from autotrading.application.flows.confirm_reconciliation import ConfirmReconciliationCommand
from autotrading.application.flows.list_reconciliation_alarms import ListReconciliationAlarmsCommand
from autotrading.application.flows.read_account_reconciliation import (
    AccountReconciliationStatus,
    ReadAccountReconciliationCommand,
)
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.deviation_threshold import DeviationThreshold
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm


class DeviationThresholdRequest(BaseModel):
    """The threshold of the balance deviation of the account, in percent of the expected balance (R3.3.1)."""

    percent: Decimal


class DeviationThresholdResponse(BaseModel):
    percent: str

    @classmethod
    def of(cls, threshold: DeviationThreshold) -> DeviationThresholdResponse:
        return cls(percent=amount_text(threshold.percent))


class BalanceComparisonResponse(BaseModel):
    """The last comparison of the balance of the account; amounts as strings (ADR 0018)."""

    compared_at: datetime
    expected_balance: str
    read_balance: str
    deviation_percent: str

    @classmethod
    def of(cls, comparison: BalanceComparison) -> BalanceComparisonResponse:
        return cls(
            compared_at=comparison.compared_at,
            expected_balance=amount_text(comparison.expected),
            read_balance=amount_text(comparison.read),
            deviation_percent=amount_text(comparison.deviation_percent),
        )


class ReconciliationAlarmResponse(BaseModel):
    """An alarm on the balance of the account: open until confirmed (R3.3.1)."""

    expected_balance: str
    read_balance: str
    deviation_percent: str
    opened_at: datetime
    confirmed_at: datetime | None

    @classmethod
    def of(cls, alarm: ReconciliationAlarm) -> ReconciliationAlarmResponse:
        return cls(
            expected_balance=amount_text(alarm.expected_balance),
            read_balance=amount_text(alarm.read_balance),
            deviation_percent=amount_text(alarm.deviation_percent),
            opened_at=alarm.opened_at,
            confirmed_at=alarm.confirmed_at,
        )


class AccountReconciliationResponse(BaseModel):
    """Whether the balance of the account is the expected one: aligned without an open alarm (R3.3.1)."""

    aligned: bool
    threshold_percent: str
    last_comparison: BalanceComparisonResponse | None
    open_alarm: ReconciliationAlarmResponse | None

    @classmethod
    def of(cls, reconciliation: AccountReconciliationStatus) -> AccountReconciliationResponse:
        comparison, alarm = reconciliation.last_comparison, reconciliation.open_alarm
        return cls(
            aligned=reconciliation.aligned,
            threshold_percent=amount_text(reconciliation.threshold_percent),
            last_comparison=None if comparison is None else BalanceComparisonResponse.of(comparison),
            open_alarm=None if alarm is None else ReconciliationAlarmResponse.of(alarm),
        )


def reconciliation_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/accounts/{account_id}", tags=["conti"])

    @router.put("/deviation-threshold")
    def set_deviation_threshold(
        account_id: UUID,
        request: DeviationThresholdRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> DeviationThresholdResponse:
        command = SetDeviationThresholdCommand(AccountId(account_id), request.percent)
        return DeviationThresholdResponse.of(use_cases.set_deviation_threshold.execute(command))

    @router.get("/reconciliation")
    def read_account_reconciliation(
        account_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> AccountReconciliationResponse:
        command = ReadAccountReconciliationCommand(account_id)
        return AccountReconciliationResponse.of(use_cases.read_account_reconciliation.execute(command))

    @router.get("/reconciliation/alarms")
    def list_reconciliation_alarms(
        account_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> list[ReconciliationAlarmResponse]:
        command = ListReconciliationAlarmsCommand(account_id)
        alarms = use_cases.list_reconciliation_alarms.execute(command)
        return [ReconciliationAlarmResponse.of(alarm) for alarm in alarms]

    @router.post("/reconciliation/confirmation", status_code=status.HTTP_204_NO_CONTENT)
    def confirm_reconciliation(
        account_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> None:
        use_cases.confirm_reconciliation.execute(ConfirmReconciliationCommand(account_id))

    return router
