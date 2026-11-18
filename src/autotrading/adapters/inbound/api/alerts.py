import base64
import binascii
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.notifications.errors import AlertCursorInvalidError
from autotrading.application.notifications.get_alert import GetAlertCommand
from autotrading.application.notifications.list_alerts import ListAlertsCommand
from autotrading.application.notifications.resolve_alert import ResolveAlertCommand
from autotrading.domain.notifications.alert import (
    Alert,
    AlertId,
    AlertKind,
    AlertRemedy,
    AlertResourceKind,
    AlertSeverity,
    AlertState,
)
from autotrading.domain.notifications.alert_page import AlertCursor, AlertFilter, AlertPage

SEPARATOR = "|"


class AlertStateQuery(StrEnum):
    """The state the list asks for: `all` does not narrow."""

    OPEN = "open"
    RESOLVED = "resolved"
    ALL = "all"


class AlertResourceResponse(BaseModel):
    kind: AlertResourceKind
    id: UUID
    name: str


class AlertResponse(BaseModel):
    """An alert of the tenant: what asks to act, how serious it is, on which resource, and whether it is resolved."""

    id: UUID
    kind: AlertKind
    title: str
    severity: AlertSeverity
    state: AlertState
    resource: AlertResourceResponse
    opened_at: datetime
    resolved_at: datetime | None

    @classmethod
    def of(cls, alert: Alert) -> AlertResponse:
        cause = alert.cause
        resource = cause.resource
        return cls(
            id=alert.id.value,
            kind=cause.kind,
            title=cause.kind.heading,
            severity=alert.severity,
            state=alert.state,
            resource=AlertResourceResponse(kind=resource.kind, id=resource.resource_id, name=resource.name),
            opened_at=alert.opened_at,
            resolved_at=alert.resolved_at,
        )


class AlertValueResponse(BaseModel):
    label: str
    value: str


class AlertDetailResponse(AlertResponse):
    """The alert with the values read when it opened and the commands that resolve it now; none once resolved."""

    values: list[AlertValueResponse]
    commands: list[AlertRemedy]

    @classmethod
    def of(cls, alert: Alert) -> AlertDetailResponse:
        return cls(
            **AlertResponse.of(alert).model_dump(),
            values=[AlertValueResponse(label=value.label, value=value.value) for value in alert.cause.values],
            commands=list(alert.commands),
        )


class AlertPageResponse(BaseModel):
    """At most 50 alerts, newest first; `next` is the `cursor` of the following page, null on the last one. `count`
    covers every alert of the filter, not only the page."""

    items: list[AlertResponse]
    next: str | None
    count: int

    @classmethod
    def of(cls, page: AlertPage) -> AlertPageResponse:
        return cls(
            items=[AlertResponse.of(alert) for alert in page.alerts],
            next=None if page.next is None else alert_cursor_text(page.next),
            count=page.count,
        )


class AlertsSummaryResponse(BaseModel):
    open_count: int


def alert_cursor_text(cursor: AlertCursor) -> str:
    plain = SEPARATOR.join((cursor.opened_at.isoformat(), str(cursor.alert_id)))
    return base64.urlsafe_b64encode(plain.encode()).decode()


def alert_cursor_of(text: str) -> AlertCursor:
    try:
        opened_at, alert_id = base64.urlsafe_b64decode(text.encode()).decode().split(SEPARATOR)
        return AlertCursor(datetime.fromisoformat(opened_at), UUID(alert_id))
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise AlertCursorInvalidError from error


def alert_filter_of(  # noqa: PLR0913, PLR0917 - one parameter for each filter of the list
    state: AlertStateQuery = AlertStateQuery.OPEN,
    severity: AlertSeverity | None = None,
    resource_kind: AlertResourceKind | None = None,
    resource_id: UUID | None = None,
    since: Annotated[datetime | None, Query(description="aperti dall'istante incluso")] = None,
    until: Annotated[datetime | None, Query(description="aperti fino all'istante escluso")] = None,
) -> AlertFilter:
    chosen = None if state is AlertStateQuery.ALL else AlertState(state.value)
    return AlertFilter(chosen, severity, resource_kind, resource_id, since, until)


def alert_cursor_query(
    cursor: Annotated[str | None, Query(description="`next` della pagina precedente")] = None,
) -> AlertCursor | None:
    return None if cursor is None else alert_cursor_of(cursor)


def alerts_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/alerts", tags=["avvisi"])

    @router.get("")
    def list_alerts(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        criteria: Annotated[AlertFilter, Depends(alert_filter_of)],
        cursor: Annotated[AlertCursor | None, Depends(alert_cursor_query)],
    ) -> AlertPageResponse:
        return AlertPageResponse.of(use_cases.list_alerts.execute(ListAlertsCommand(criteria, cursor)))

    @router.get("/summary")
    def read_alerts_summary(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> AlertsSummaryResponse:
        return AlertsSummaryResponse(open_count=use_cases.count_open_alerts.execute())

    @router.get("/{alert_id}")
    def get_alert(
        alert_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> AlertDetailResponse:
        return AlertDetailResponse.of(use_cases.get_alert.execute(GetAlertCommand(AlertId(alert_id))))

    @router.post("/{alert_id}/resolution", status_code=status.HTTP_204_NO_CONTENT)
    def resolve_alert(alert_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> None:
        use_cases.resolve_alert.execute(ResolveAlertCommand(AlertId(alert_id)))

    return router
