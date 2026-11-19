from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from autotrading.domain.notifications.errors import InvalidInboxNotificationError
from autotrading.domain.notifications.inbox_notification import (
    INBOX_RETENTION,
    InboxNotification,
    InboxNotificationId,
)
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_target import NotificationTarget

NOTIFIED_AT = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)
FLOW = uuid4()


def a_notification(at: datetime = NOTIFIED_AT) -> InboxNotification:
    return InboxNotification.of(Notification.cycle_failed(FLOW, "alfa", "exchange non raggiungibile"), at)


def test_a_notification_is_kept_unread_with_its_icon_heading_values_and_pages() -> None:
    notification = Notification.cycle_failed(FLOW, "alfa", "exchange non raggiungibile")

    kept = InboxNotification.of(notification, NOTIFIED_AT)

    assert (kept.icon, kept.title, kept.text) == (
        notification.icon,
        "alfa: ciclo fallito",
        "Errore: exchange non raggiungibile",
    )
    assert kept.targets == (NotificationTarget.flow(FLOW),)
    assert (kept.notified_at, kept.read_at, kept.is_read) == (NOTIFIED_AT, None, False)


def test_every_kept_notification_has_an_identity_of_its_own() -> None:
    assert a_notification().id != a_notification().id


def test_a_notification_without_values_keeps_an_empty_text() -> None:
    bare = Notification("alfa", "in pausa", (), None, "!")

    assert InboxNotification.of(bare, NOTIFIED_AT).text == ""


def test_the_test_notification_is_kept_too() -> None:
    assert InboxNotification.of(Notification.test(), NOTIFIED_AT).title == "AutoTrading: prova delle notifiche"


def test_the_state_of_the_flow_closes_the_text() -> None:
    notification = Notification.cycle_failed(FLOW, "alfa", "errore")

    kept = InboxNotification.of(notification, NOTIFIED_AT)

    assert kept.text.splitlines() == list(notification.body_lines())


def test_reading_keeps_the_first_instant_it_was_read() -> None:
    first = NOTIFIED_AT + timedelta(minutes=5)

    read = a_notification().read(first).read(first + timedelta(hours=1))

    assert (read.is_read, read.read_at) == (True, first)


def test_a_notification_older_than_the_retention_is_forgotten() -> None:
    kept = a_notification()

    assert not kept.forgotten_at(NOTIFIED_AT + INBOX_RETENTION)
    assert kept.forgotten_at(NOTIFIED_AT + INBOX_RETENTION + timedelta(seconds=1))
    assert timedelta(days=90) == INBOX_RETENTION


def test_an_instant_without_its_zone_is_a_defect() -> None:
    with pytest.raises(InvalidInboxNotificationError):
        a_notification(datetime(2026, 11, 19, 9, 0))


def test_the_identity_of_a_kept_notification_is_new_each_time() -> None:
    assert InboxNotificationId.new() != InboxNotificationId.new()
