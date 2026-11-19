import base64
import binascii
from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.notifications.errors import InboxCursorInvalidError
from autotrading.application.notifications.list_inbox_notifications import ListInboxNotificationsCommand
from autotrading.application.notifications.mark_notification_read import MarkNotificationReadCommand
from autotrading.domain.notifications.inbox_notification import InboxNotification, InboxNotificationId
from autotrading.domain.notifications.inbox_page import InboxCursor, InboxPage
from autotrading.domain.notifications.notification_target import NotificationTarget, TargetKind

SEPARATOR = "|"


class InboxTargetResponse(BaseModel):
    """A page the notification leads to, by what finds it: the flow and, for a position, its asset and the instant it
    closed; or the alert it opened. The dashboard builds the address (ADR notifiche-nell-app-salvate-per-tenant)."""

    kind: TargetKind
    label: str
    flow_id: UUID | None
    asset: str | None
    closed_at: datetime | None
    alert_id: UUID | None

    @classmethod
    def of(cls, target: NotificationTarget) -> InboxTargetResponse:
        of_alert = target.kind is TargetKind.ALERT
        return cls(
            kind=target.kind,
            label=target.label,
            flow_id=None if of_alert else target.owner_id,
            asset=target.asset,
            closed_at=target.closed_at,
            alert_id=target.owner_id if of_alert else None,
        )


class InboxNotificationResponse(BaseModel):
    """A notification of the bell: its icon, title and values, when it was generated, when it was read, if it was, and
    the pages it leads to, the first one where choosing it leads."""

    id: UUID
    icon: str
    title: str
    text: str
    notified_at: datetime
    read_at: datetime | None
    targets: list[InboxTargetResponse]

    @classmethod
    def of(cls, notification: InboxNotification) -> InboxNotificationResponse:
        return cls(
            id=notification.id.value,
            icon=notification.icon,
            title=notification.title,
            text=notification.text,
            notified_at=notification.notified_at,
            read_at=notification.read_at,
            targets=[InboxTargetResponse.of(target) for target in notification.targets],
        )


class InboxPageResponse(BaseModel):
    """At most 20 notifications, newest first; `next` is the `cursor` of the following page, null on the last one."""

    items: list[InboxNotificationResponse]
    next: str | None

    @classmethod
    def of(cls, page: InboxPage) -> InboxPageResponse:
        return cls(
            items=[InboxNotificationResponse.of(notification) for notification in page.notifications],
            next=None if page.next is None else inbox_cursor_text(page.next),
        )


class InboxSummaryResponse(BaseModel):
    unread_count: int


def inbox_cursor_text(cursor: InboxCursor) -> str:
    plain = SEPARATOR.join((cursor.notified_at.isoformat(), str(cursor.notification_id)))
    return base64.urlsafe_b64encode(plain.encode()).decode()


def inbox_cursor_of(text: str) -> InboxCursor:
    try:
        notified_at, notification_id = base64.urlsafe_b64decode(text.encode()).decode().split(SEPARATOR)
        return InboxCursor(datetime.fromisoformat(notified_at), UUID(notification_id))
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise InboxCursorInvalidError from error


def inbox_cursor_query(
    cursor: Annotated[str | None, Query(description="`next` della pagina precedente")] = None,
) -> InboxCursor | None:
    return None if cursor is None else inbox_cursor_of(cursor)


def notification_inbox_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/notifications/inbox", tags=["campanello delle notifiche"])

    @router.get("")
    def list_inbox_notifications(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        cursor: Annotated[InboxCursor | None, Depends(inbox_cursor_query)],
    ) -> InboxPageResponse:
        page = use_cases.list_inbox_notifications.execute(ListInboxNotificationsCommand(cursor))
        return InboxPageResponse.of(page)

    @router.get("/summary")
    def read_inbox_summary(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> InboxSummaryResponse:
        return InboxSummaryResponse(unread_count=use_cases.count_unread_notifications.execute())

    @router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
    def mark_all_notifications_read(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> None:
        use_cases.mark_all_notifications_read.execute()

    @router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
    def mark_notification_read(
        notification_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> None:
        command = MarkNotificationReadCommand(InboxNotificationId(notification_id))
        use_cases.mark_notification_read.execute(command)

    return router
