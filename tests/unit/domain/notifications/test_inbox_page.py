from datetime import UTC, datetime, timedelta
from uuid import uuid4

from autotrading.domain.notifications.inbox_notification import InboxNotification
from autotrading.domain.notifications.inbox_page import INBOX_PAGE_SIZE, InboxCursor, InboxPage
from autotrading.domain.notifications.notification import Notification

NINE = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)


def kept(minutes: int) -> InboxNotification:
    return InboxNotification.of(Notification.cycle_failed(uuid4(), "alfa", "errore"), NINE + timedelta(minutes=minutes))


def test_the_cursor_is_the_place_of_a_notification_by_instant_then_identity() -> None:
    notification = kept(0)

    cursor = InboxCursor.of(notification)

    assert (cursor.notified_at, cursor.notification_id) == (NINE, notification.id.value)
    assert InboxCursor.of(kept(1)) > cursor


def test_a_cursor_admits_only_the_notifications_older_than_its_place() -> None:
    older, newer = kept(0), kept(1)
    cursor = InboxCursor.of(newer)

    assert cursor.admits(older)
    assert not cursor.admits(newer)


def test_a_page_from_one_more_than_the_limit_says_where_the_next_starts() -> None:
    newest_first = [kept(2), kept(1), kept(0)]

    page = InboxPage.of(newest_first, 2)

    assert page.notifications == tuple(newest_first[:2])
    assert page.next == InboxCursor.of(newest_first[1])


def test_the_last_page_has_no_next() -> None:
    newest_first = [kept(1), kept(0)]

    assert InboxPage.of(newest_first, 2).next is None
    assert InboxPage.of([], 2) == InboxPage((), None)


def test_the_bell_shows_twenty_notifications_a_page() -> None:
    assert INBOX_PAGE_SIZE == 20
