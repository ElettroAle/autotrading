from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.interval_query import IntervalEnd, IntervalStart
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.list_account_capital_changes import ListAccountCapitalChangesCommand
from autotrading.application.flows.list_capital_changes import ListCapitalChangesCommand
from autotrading.domain.flows.capital_history import CapitalHistoryEntry, CapitalHistoryPage
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.statistics_period import TimeWindow


class CapitalChangeResponse(BaseModel):
    """A row of the history of the capital (R3.4.2): a deposit or a withdrawal of the account has no flow and no capital
    before and after."""

    changed_at: datetime
    flow_id: UUID | None
    flow: str | None
    reason: str
    # Amounts travel as strings, so no precision is lost on the way (ADR 0018).
    amount: str
    previous: str | None
    new: str | None

    @classmethod
    def of(cls, entry: CapitalHistoryEntry) -> CapitalChangeResponse:
        return cls(
            changed_at=entry.occurred_at,
            flow_id=None if entry.flow_id is None else entry.flow_id.value,
            flow=entry.flow_name,
            reason=entry.reason.value,
            amount=amount_text(entry.amount),
            previous=None if entry.previous is None else amount_text(entry.previous),
            new=None if entry.new is None else amount_text(entry.new),
        )


class CapitalChangePageResponse(BaseModel):
    """A page of the history of the capital, from the most recent row, with how many rows the period holds (R3.4.2)."""

    page: int
    has_next: bool
    total: int
    currency: str
    changes: list[CapitalChangeResponse]

    @classmethod
    def of(cls, page: CapitalHistoryPage) -> CapitalChangePageResponse:
        return cls(
            page=page.number,
            has_next=page.has_next,
            total=page.total,
            currency=page.currency,
            changes=[CapitalChangeResponse.of(entry) for entry in page.entries],
        )


def window_of(since: IntervalStart = None, until: IntervalEnd = None) -> TimeWindow:
    return TimeWindow.of_minutes(since, until)


def capital_changes_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["capitale"])

    @router.get("/flows/{flow_id}/capital-changes")
    def list_capital_changes(
        flow_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        window: Annotated[TimeWindow, Depends(window_of)],
        page: Annotated[int, Query()] = 1,
    ) -> CapitalChangePageResponse:
        command = ListCapitalChangesCommand(FlowId(flow_id), page, window)
        return CapitalChangePageResponse.of(use_cases.list_capital_changes.execute(command))

    @router.get("/accounts/{account_id}/capital-changes")
    def list_account_capital_changes(
        account_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        window: Annotated[TimeWindow, Depends(window_of)],
        page: Annotated[int, Query()] = 1,
    ) -> CapitalChangePageResponse:
        command = ListAccountCapitalChangesCommand(account_id, page, window)
        return CapitalChangePageResponse.of(use_cases.list_account_capital_changes.execute(command))

    return router
