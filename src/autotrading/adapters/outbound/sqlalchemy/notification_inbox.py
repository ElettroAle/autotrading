from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Connection,
    Engine,
    RowMapping,
    delete,
    func,
    insert,
    literal,
    select,
    tuple_,
    update,
)
from sqlalchemy.exc import SQLAlchemyError

from autotrading.adapters.outbound.sqlalchemy.tables import inbox_notifications
from autotrading.application.notifications.errors import (
    InboxNotificationNotFoundError,
    NotificationInboxUnavailableError,
)
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.inbox_notification import (
    INBOX_RETENTION,
    InboxNotification,
    InboxNotificationId,
)
from autotrading.domain.notifications.inbox_page import INBOX_PAGE_SIZE, InboxCursor, InboxPage
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_target import NotificationTarget, TargetKind
from autotrading.domain.tenancy.tenant_id import TenantId

UNREAD = inbox_notifications.c.read_at.is_(None)


class SqlAlchemyNotificationInboxAdapter:
    """Bound to the tenant of the request or of the cycle: every transaction declares it, and row level security does
    the rest (ADR notifiche-nell-app-salvate-per-tenant).

    Each notification is kept with the instant the worker generated it; the instant it is read is that of the database.
    Keeping one forgets those of the tenant older than the retention, without a job of its own. The list goes by keyset
    on instant and id, newest first (ADR 0074).
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def add(self, notification: Notification, at: datetime) -> None:
        row = _row_of(InboxNotification.of(self._tenant_id, notification, at), self._tenant_id)
        try:
            with self._transaction() as connection:
                connection.execute(
                    delete(inbox_notifications).where(inbox_notifications.c.notified_at < at - INBOX_RETENTION)
                )
                connection.execute(insert(inbox_notifications).values(row))
        except SQLAlchemyError as error:
            raise NotificationInboxUnavailableError from error

    def list(self, cursor: InboxCursor | None) -> InboxPage:
        columns = inbox_notifications.c
        page = (
            select(inbox_notifications)
            .where(*_after(cursor))
            .order_by(columns.notified_at.desc(), columns.id.desc())
            .limit(INBOX_PAGE_SIZE + 1)
        )
        with self._transaction() as connection:
            rows = connection.execute(page).mappings().all()
        return InboxPage.of([_inbox_notification_of(row) for row in rows], INBOX_PAGE_SIZE)

    def unread_count(self) -> int:
        with self._transaction() as connection:
            return connection.execute(select(func.count()).select_from(inbox_notifications).where(UNREAD)).scalar_one()

    def mark_read(self, notification_id: InboxNotificationId) -> None:
        columns = inbox_notifications.c
        reading = (
            update(inbox_notifications)
            .where(columns.id == notification_id.value)
            .values(read_at=func.coalesce(columns.read_at, func.now()))
            .returning(columns.id)
        )
        with self._transaction() as connection:
            read = connection.execute(reading).scalar_one_or_none()
        if read is None:
            raise InboxNotificationNotFoundError

    def mark_all_read(self) -> None:
        with self._transaction() as connection:
            connection.execute(update(inbox_notifications).where(UNREAD).values(read_at=func.now()))

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _row_of(notification: InboxNotification, tenant_id: TenantId) -> dict[str, object]:
    if notification.tenant_id != tenant_id:
        raise CrossTenantAccessError
    return {
        "id": notification.id.value,
        "tenant_id": notification.tenant_id.value,
        "notified_at": notification.notified_at,
        "icon": notification.icon,
        "title": notification.title,
        "text": notification.text,
        "targets": [_target_row(target) for target in notification.targets],
    }


def _target_row(target: NotificationTarget) -> dict[str, str | None]:
    return {
        "kind": target.kind.value,
        "owner_id": str(target.owner_id),
        "asset": target.asset,
        "closed_at": None if target.closed_at is None else target.closed_at.isoformat(),
    }


def _target_of(row: dict[str, str | None]) -> NotificationTarget:
    closed_at = row["closed_at"]
    return NotificationTarget(
        TargetKind(str(row["kind"])),
        UUID(str(row["owner_id"])),
        row["asset"],
        None if closed_at is None else datetime.fromisoformat(closed_at),
    )


def _inbox_notification_of(row: RowMapping) -> InboxNotification:
    return InboxNotification(
        TenantId(row["tenant_id"]),
        InboxNotificationId(row["id"]),
        row["notified_at"],
        row["icon"],
        row["title"],
        row["text"],
        tuple(_target_of(target) for target in row["targets"]),
        row["read_at"],
    )


def _after(cursor: InboxCursor | None) -> list[ColumnElement[bool]]:
    if cursor is None:
        return []
    columns = inbox_notifications.c
    return [
        tuple_(columns.notified_at, columns.id) < tuple_(literal(cursor.notified_at), literal(cursor.notification_id))
    ]
