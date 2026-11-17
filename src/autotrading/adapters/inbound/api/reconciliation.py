import base64
import binascii
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.accounts.set_deviation_threshold import SetDeviationThresholdCommand
from autotrading.application.flows.confirm_reconciliation import ConfirmReconciliationCommand
from autotrading.application.flows.errors import UnattributableCursorInvalidError
from autotrading.application.flows.list_reconciliation_alarms import ListReconciliationAlarmsCommand
from autotrading.application.flows.list_unattributable import ListUnattributableCommand
from autotrading.application.flows.read_account_reconciliation import (
    AccountReconciliationStatus,
    ReadAccountReconciliationCommand,
)
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.deviation_threshold import DeviationThreshold
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.unattributable import UnattributableKind
from autotrading.domain.flows.unattributable_page import (
    RecordedUnattributable,
    UnattributableCursor,
    UnattributableFilter,
    UnattributablePage,
)

SEPARATOR = "|"


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


class UnattributableResponse(BaseModel):
    """A case no flow explains (R1.6.2): the change of the balance, or the size of a position or an execution, as text
    without trailing zeros (ADR 0047)."""

    detected_at: datetime
    kind: UnattributableKind
    asset: str | None
    amount: str

    @classmethod
    def of(cls, case: RecordedUnattributable) -> UnattributableResponse:
        item = case.item
        return cls(detected_at=item.detected_at, kind=item.kind, asset=item.asset, amount=amount_text(item.amount))


class UnattributablePageResponse(BaseModel):
    """At most 50 cases, newest first; `next` is the `cursor` of the following page, null on the last one. `count` and
    `net_change`, the net of the changes of the balance, cover every case of the filter, not only the page."""

    items: list[UnattributableResponse]
    next: str | None
    count: int
    net_change: str

    @classmethod
    def of(cls, page: UnattributablePage) -> UnattributablePageResponse:
        return cls(
            items=[UnattributableResponse.of(case) for case in page.cases],
            next=None if page.next is None else unattributable_cursor_text(page.next),
            count=page.count,
            net_change=amount_text(page.net_change),
        )


def unattributable_cursor_text(cursor: UnattributableCursor) -> str:
    plain = SEPARATOR.join((cursor.detected_at.isoformat(), str(cursor.item_id)))
    return base64.urlsafe_b64encode(plain.encode()).decode()


def unattributable_cursor_of(text: str) -> UnattributableCursor:
    try:
        detected_at, item_id = base64.urlsafe_b64decode(text.encode()).decode().split(SEPARATOR)
        return UnattributableCursor(datetime.fromisoformat(detected_at), UUID(item_id))
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise UnattributableCursorInvalidError from error


def unattributable_filter_of(
    kind: UnattributableKind | None = None,
    since: Annotated[datetime | None, Query(description="dall'istante incluso")] = None,
    until: Annotated[datetime | None, Query(description="all'istante escluso")] = None,
) -> UnattributableFilter:
    return UnattributableFilter(kind, since, until)


def unattributable_cursor_query(
    cursor: Annotated[str | None, Query(description="`next` della pagina precedente")] = None,
) -> UnattributableCursor | None:
    return None if cursor is None else unattributable_cursor_of(cursor)


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

    @router.get("/reconciliation/unattributable")
    def list_unattributable(
        account_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        criteria: Annotated[UnattributableFilter, Depends(unattributable_filter_of)],
        cursor: Annotated[UnattributableCursor | None, Depends(unattributable_cursor_query)],
    ) -> UnattributablePageResponse:
        command = ListUnattributableCommand(account_id, criteria, cursor)
        return UnattributablePageResponse.of(use_cases.list_unattributable.execute(command))

    @router.post("/reconciliation/confirmation", status_code=status.HTTP_204_NO_CONTENT)
    def confirm_reconciliation(
        account_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> None:
        use_cases.confirm_reconciliation.execute(ConfirmReconciliationCommand(account_id))

    return router
