import base64
import binascii
from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.errors import OperationsCursorInvalidError
from autotrading.application.flows.list_account_operations import ListAccountOperationsCommand
from autotrading.application.flows.list_flow_operations import ListFlowOperationsCommand
from autotrading.domain.flows.free_capital import amount_text
from autotrading.domain.flows.operations import (
    Operation,
    OperationCursor,
    OperationSource,
    OperationsPage,
    OperationsQuery,
)

PURCHASE = "acquisto"
SALE = "vendita"
SEPARATOR = "|"


class OperationResponse(BaseModel):
    """A row of the ledger (ADR 0063, ADR 0074): amounts as text without trailing zeros (ADR 0047).

    An execution has side, size and price; a funding payment has the amount paid (positive when received).
    """

    occurred_at: datetime
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
            asset=operation.asset,
            kind=operation.kind,
            side=None if size is None else (PURCHASE if size > 0 else SALE),
            size=None if size is None else amount_text(abs(size)),
            price=None if operation.price is None else amount_text(operation.price),
            fee=amount_text(operation.fee),
            realized_pnl=amount_text(operation.realized_pnl),
            funding=amount_text(operation.funding),
        )


class OperationsPageResponse(BaseModel):
    """At most 50 rows, newest first; `next` is the `after` of the following page, null on the last one."""

    operations: list[OperationResponse]
    next: str | None

    @classmethod
    def of(cls, page: OperationsPage) -> OperationsPageResponse:
        return cls(
            operations=[OperationResponse.of(operation) for operation in page.operations],
            next=None if page.next is None else cursor_text(page.next),
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
    ) -> OperationsPageResponse:
        command = ListAccountOperationsCommand(account_id, query)
        return OperationsPageResponse.of(use_cases.list_account_operations.execute(command))

    return router
