import base64
import binascii
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.operations_csv import csv_lines, side_of
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.errors import OperationsCursorInvalidError
from autotrading.application.flows.export_account_operations import ExportAccountOperationsCommand
from autotrading.application.flows.export_flow_operations import ExportFlowOperationsCommand
from autotrading.application.flows.list_account_operations import ListAccountOperationsCommand
from autotrading.application.flows.list_flow_operations import ListFlowOperationsCommand
from autotrading.domain.flows.operations import (
    AccountScope,
    Operation,
    OperationCursor,
    OperationSource,
    OperationsQuery,
    OperationsReport,
    OperationsTotals,
)

SEPARATOR = "|"
CSV = "text/csv; charset=utf-8"


class OperationResponse(BaseModel):
    """A row of the ledger (ADR 0063, ADR 0074): amounts as text without trailing zeros (ADR 0047).

    An execution has side, size and price; a funding payment has the amount paid (positive when received). `flow` is
    the name of the flow of the row, null when it belongs to no flow (ADR 0080).
    """

    occurred_at: datetime
    flow: str | None
    asset: str
    kind: str
    side: str | None
    size: str | None
    price: str | None
    fee: str
    realized_pnl: str
    funding: str

    @classmethod
    def of(cls, operation: Operation) -> OperationResponse:
        size = operation.size
        return cls(
            occurred_at=operation.occurred_at,
            flow=operation.flow,
            asset=operation.asset,
            kind=operation.kind,
            side=side_of(operation),
            size=None if size is None else amount_text(abs(size)),
            price=None if operation.price is None else amount_text(operation.price),
            fee=amount_text(operation.fee),
            realized_pnl=amount_text(operation.realized_pnl),
            funding=amount_text(operation.funding),
        )


class OperationsTotalsResponse(BaseModel):
    """The totals of every row of the filter, not only of the page (ADR 0080)."""

    count: int
    realized_pnl: str
    fees: str
    funding: str

    @classmethod
    def of(cls, totals: OperationsTotals) -> OperationsTotalsResponse:
        return cls(
            count=totals.count,
            realized_pnl=amount_text(totals.realized_pnl),
            fees=amount_text(totals.fees),
            funding=amount_text(totals.funding),
        )


class OperationsPageResponse(BaseModel):
    """At most 50 rows, newest first; `next` is the `after` of the following page, null on the last one."""

    operations: list[OperationResponse]
    next: str | None
    totals: OperationsTotalsResponse

    @classmethod
    def of(cls, report: OperationsReport) -> OperationsPageResponse:
        page = report.page
        return cls(
            operations=[OperationResponse.of(operation) for operation in page.operations],
            next=None if page.next is None else cursor_text(page.next),
            totals=OperationsTotalsResponse.of(report.totals),
        )


def cursor_text(cursor: OperationCursor) -> str:
    plain = SEPARATOR.join((cursor.occurred_at.isoformat(), str(int(cursor.source)), str(cursor.row_id)))
    return base64.urlsafe_b64encode(plain.encode()).decode()


def cursor_of(text: str) -> OperationCursor:
    try:
        occurred_at, source, row_id = base64.urlsafe_b64decode(text.encode()).decode().split(SEPARATOR)
        return OperationCursor(datetime.fromisoformat(occurred_at), OperationSource(int(source)), int(row_id))
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise OperationsCursorInvalidError from error


def query_of(
    asset: str | None = None,
    since: Annotated[datetime | None, Query(alias="from")] = None,
    until: Annotated[datetime | None, Query(alias="to")] = None,
    after: str | None = None,
) -> OperationsQuery:
    """The filters of a page: an asset, the period from `from` included to `to` excluded, the page after a row."""
    return OperationsQuery(asset, since, until, None if after is None else cursor_of(after))


def filters_of(
    asset: str | None = None,
    since: Annotated[datetime | None, Query(alias="from")] = None,
    until: Annotated[datetime | None, Query(alias="to")] = None,
) -> OperationsQuery:
    """The filters of an export: an asset and the period from `from` included to `to` excluded, every page."""
    return OperationsQuery(asset, since, until)


def csv_response(operations: Iterator[Operation]) -> StreamingResponse:
    headers = {"Content-Disposition": 'attachment; filename="operazioni.csv"'}
    return StreamingResponse(csv_lines(operations), media_type=CSV, headers=headers)


def operations_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.get("/flows/{flow_id}/operations")
    def list_flow_operations(
        flow_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        query: Annotated[OperationsQuery, Depends(query_of)],
    ) -> OperationsPageResponse:
        command = ListFlowOperationsCommand(flow_id, query)
        return OperationsPageResponse.of(use_cases.list_flow_operations.execute(command))

    @router.get("/accounts/{account_id}/operations")
    def list_account_operations(
        account_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        query: Annotated[OperationsQuery, Depends(query_of)],
        scope: AccountScope = AccountScope.UNATTRIBUTED,
    ) -> OperationsPageResponse:
        command = ListAccountOperationsCommand(account_id, query, scope)
        return OperationsPageResponse.of(use_cases.list_account_operations.execute(command))

    @router.get("/flows/{flow_id}/operations.csv", response_class=StreamingResponse)
    def export_flow_operations(
        flow_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        query: Annotated[OperationsQuery, Depends(filters_of)],
    ) -> StreamingResponse:
        command = ExportFlowOperationsCommand(flow_id, query)
        return csv_response(use_cases.export_flow_operations.execute(command))

    @router.get("/accounts/{account_id}/operations.csv", response_class=StreamingResponse)
    def export_account_operations(
        account_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        query: Annotated[OperationsQuery, Depends(filters_of)],
        scope: AccountScope = AccountScope.UNATTRIBUTED,
    ) -> StreamingResponse:
        command = ExportAccountOperationsCommand(account_id, query, scope)
        return csv_response(use_cases.export_account_operations.execute(command))

    return router
