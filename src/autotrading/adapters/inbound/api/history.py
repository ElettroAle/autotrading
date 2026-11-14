import base64
import binascii
from collections.abc import Callable
from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.closed_positions import ClosedPositionResponse
from autotrading.adapters.inbound.api.cycles import CycleSummaryResponse
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.errors import HistoryCursorInvalidError
from autotrading.application.flows.query_closed_position_history import QueryClosedPositionHistoryCommand
from autotrading.application.flows.query_cycle_history import QueryCycleHistoryCommand
from autotrading.application.flows.query_order_history import QueryOrderHistoryCommand
from autotrading.domain.flows.history import (
    ClosedPositionHistoryEntry,
    CycleHistoryEntry,
    HistoryCursor,
    HistoryFilter,
    HistoryPage,
    OrderExecution,
    OrderHistoryEntry,
)
from autotrading.domain.flows.statistics_period import StatisticsPeriod

SEPARATOR = "|"


class HistoryCycleResponse(CycleSummaryResponse):
    """A cycle of the history, with its flow and the configuration version in force when it ran (R2.5.1)."""

    flow_id: UUID
    flow: str
    version: int | None

    @classmethod
    def of_entry(cls, entry: CycleHistoryEntry) -> HistoryCycleResponse:
        summary = CycleSummaryResponse.of(entry.record)
        return cls(**summary.model_dump(), flow_id=entry.record.flow_id, flow=entry.flow_name, version=entry.version)


class HistoryCyclesPageResponse(BaseModel):
    """At most 50 cycles, newest first; `next` is the `after` of the following page, null on the last one."""

    cycles: list[HistoryCycleResponse]
    next: str | None

    @classmethod
    def of(cls, page: HistoryPage[CycleHistoryEntry]) -> HistoryCyclesPageResponse:
        return cls(cycles=[HistoryCycleResponse.of_entry(entry) for entry in page.entries], next=_next_of(page.next))


class HistoryClosedPositionResponse(ClosedPositionResponse):
    """A closed position of the history, with its flow (R2.5.1)."""

    id: UUID
    flow_id: UUID
    flow: str

    @classmethod
    def of_entry(cls, entry: ClosedPositionHistoryEntry) -> HistoryClosedPositionResponse:
        position = ClosedPositionResponse.of(entry.position)
        return cls(
            **position.model_dump(), id=entry.position_id, flow_id=entry.position.flow_id.value, flow=entry.flow_name
        )


class HistoryClosedPositionsPageResponse(BaseModel):
    """At most 50 closed positions, newest close first; `next` is the `after` of the following page."""

    positions: list[HistoryClosedPositionResponse]
    next: str | None

    @classmethod
    def of(cls, page: HistoryPage[ClosedPositionHistoryEntry]) -> HistoryClosedPositionsPageResponse:
        positions = [HistoryClosedPositionResponse.of_entry(entry) for entry in page.entries]
        return cls(positions=positions, next=_next_of(page.next))


class OrderExecutionResponse(BaseModel):
    """An execution of an order: price, quantity and fee as text without trailing zeros (ADR 0018)."""

    executed_at: datetime
    price: str
    size: str
    fee: str

    @classmethod
    def of(cls, execution: OrderExecution) -> OrderExecutionResponse:
        return cls(
            executed_at=execution.executed_at,
            price=amount_text(execution.price),
            size=amount_text(abs(execution.size)),
            fee=amount_text(execution.fee),
        )


class HistoryOrderResponse(BaseModel):
    """An order of the history with its outcome and its executions; `flow` is null for an order of no flow."""

    id: UUID
    created_at: datetime
    account_id: UUID
    account: str
    flow_id: UUID | None
    flow: str | None
    asset: str
    direction: str
    closing: bool
    leverage: int
    requested_size: str
    status: str
    origin: str
    executions: list[OrderExecutionResponse]

    @classmethod
    def of(cls, entry: OrderHistoryEntry) -> HistoryOrderResponse:
        return cls(
            id=entry.order_id,
            created_at=entry.created_at,
            account_id=entry.account_id,
            account=entry.account_name,
            flow_id=entry.flow_id,
            flow=entry.flow_name,
            asset=entry.asset,
            direction=entry.direction,
            closing=entry.closing,
            leverage=entry.leverage,
            requested_size=amount_text(entry.requested_size),
            status=entry.status,
            origin=entry.origin,
            executions=[OrderExecutionResponse.of(execution) for execution in entry.executions],
        )


class HistoryOrdersPageResponse(BaseModel):
    """At most 50 orders, newest first; `next` is the `after` of the following page, null on the last one."""

    orders: list[HistoryOrderResponse]
    next: str | None

    @classmethod
    def of(cls, page: HistoryPage[OrderHistoryEntry]) -> HistoryOrdersPageResponse:
        return cls(orders=[HistoryOrderResponse.of(entry) for entry in page.entries], next=_next_of(page.next))


def cursor_text(cursor: HistoryCursor) -> str:
    plain = SEPARATOR.join((cursor.at.isoformat(), str(cursor.key)))
    return base64.urlsafe_b64encode(plain.encode()).decode()


def cursor_of(text: str) -> HistoryCursor:
    try:
        at, key = base64.urlsafe_b64decode(text.encode()).decode().split(SEPARATOR)
        return HistoryCursor(datetime.fromisoformat(at), UUID(key))
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise HistoryCursorInvalidError from error


def period_of(
    period: Annotated[str, Query(description="all, 7d, 30d o range")] = "all",
    first_day: Annotated[date | None, Query(alias="from", description="primo giorno di un intervallo")] = None,
    last_day: Annotated[date | None, Query(alias="to", description="ultimo giorno di un intervallo")] = None,
) -> StatisticsPeriod:
    return StatisticsPeriod.named(period, first_day, last_day)


def criteria_of(
    period: Annotated[StatisticsPeriod, Depends(period_of)],
    flow_id: UUID | None = None,
    account_id: UUID | None = None,
    asset: str | None = None,
    version: Annotated[int | None, Query(ge=1, description="versione della configurazione di un flusso")] = None,
) -> HistoryFilter:
    """The filters of a history, in any combination; a version needs its flow (R2.5.1)."""
    return HistoryFilter(flow_id, account_id, period, asset, version)


def after_of(
    after: Annotated[str | None, Query(description="`next` della pagina precedente")] = None,
) -> HistoryCursor | None:
    return None if after is None else cursor_of(after)


def history_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/history", tags=["storico"])

    @router.get("/cycles")
    def query_cycle_history(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        criteria: Annotated[HistoryFilter, Depends(criteria_of)],
        after: Annotated[HistoryCursor | None, Depends(after_of)],
    ) -> HistoryCyclesPageResponse:
        page = use_cases.query_cycle_history.execute(QueryCycleHistoryCommand(criteria, after))
        return HistoryCyclesPageResponse.of(page)

    @router.get("/closed-positions")
    def query_closed_position_history(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        criteria: Annotated[HistoryFilter, Depends(criteria_of)],
        after: Annotated[HistoryCursor | None, Depends(after_of)],
    ) -> HistoryClosedPositionsPageResponse:
        page = use_cases.query_closed_position_history.execute(QueryClosedPositionHistoryCommand(criteria, after))
        return HistoryClosedPositionsPageResponse.of(page)

    @router.get("/orders")
    def query_order_history(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        criteria: Annotated[HistoryFilter, Depends(criteria_of)],
        after: Annotated[HistoryCursor | None, Depends(after_of)],
    ) -> HistoryOrdersPageResponse:
        page = use_cases.query_order_history.execute(QueryOrderHistoryCommand(criteria, after))
        return HistoryOrdersPageResponse.of(page)

    return router


def _next_of(cursor: HistoryCursor | None) -> str | None:
    return None if cursor is None else cursor_text(cursor)
