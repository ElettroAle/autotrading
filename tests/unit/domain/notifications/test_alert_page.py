from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from autotrading.domain.notifications.alert import (
    Alert,
    AlertCause,
    AlertId,
    AlertResourceKind,
    AlertSeverity,
    AlertState,
)
from autotrading.domain.notifications.alert_page import AlertCursor, AlertFilter, AlertPage

ACCOUNT_ID, FLOW_ID = uuid4(), uuid4()
NINE = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


def alert(cause: AlertCause, opened_at: datetime = NINE, resolved_at: datetime | None = None) -> Alert:
    return Alert(AlertId(UUID(int=opened_at.hour)), cause, opened_at, resolved_at)


PAUSED = alert(AlertCause.flow_paused(FLOW_ID, "alfa", "credito esaurito"))
FILL = alert(AlertCause.unattributable_fill(ACCOUNT_ID, "test-1", "SOL"), NINE + timedelta(hours=1), NINE)


def test_an_empty_filter_admits_every_alert() -> None:
    assert AlertFilter().admits(PAUSED)
    assert AlertFilter().admits(FILL)


def test_the_state_admits_only_the_alerts_in_it() -> None:
    assert AlertFilter(state=AlertState.OPEN).admits(PAUSED)
    assert not AlertFilter(state=AlertState.OPEN).admits(FILL)
    assert AlertFilter(state=AlertState.RESOLVED).admits(FILL)


def test_severity_and_kind_of_resource_admit_the_alerts_that_have_them() -> None:
    assert AlertFilter(severity=AlertSeverity.CRITICAL).admits(PAUSED)
    assert not AlertFilter(severity=AlertSeverity.CRITICAL).admits(FILL)
    assert AlertFilter(resource_kind=AlertResourceKind.ACCOUNT).admits(FILL)
    assert not AlertFilter(resource_kind=AlertResourceKind.KEY).admits(FILL)


def test_the_resource_admits_only_its_alerts() -> None:
    assert AlertFilter(resource_id=FLOW_ID).admits(PAUSED)
    assert not AlertFilter(resource_id=FLOW_ID).admits(FILL)


def test_the_period_goes_from_since_included_to_until_excluded() -> None:
    assert AlertFilter(since=NINE, until=NINE + timedelta(minutes=1)).admits(PAUSED)
    assert not AlertFilter(since=NINE + timedelta(minutes=1)).admits(PAUSED)
    assert not AlertFilter(until=NINE).admits(PAUSED)


def test_after_a_cursor_only_the_older_alerts_are_admitted() -> None:
    assert AlertFilter().admits(PAUSED, AlertCursor.of(FILL))
    assert not AlertFilter().admits(FILL, AlertCursor.of(PAUSED))


def test_the_cursor_of_an_alert_is_its_opening_then_its_id() -> None:
    assert AlertCursor.of(PAUSED) == AlertCursor(NINE, PAUSED.id.value)


def test_a_page_with_one_alert_more_than_the_limit_says_where_the_next_starts() -> None:
    page = AlertPage.of([FILL, PAUSED], 1, 2)

    assert page.alerts == (FILL,)
    assert page.next == AlertCursor.of(FILL)
    assert page.count == 2


def test_the_last_page_has_no_next() -> None:
    assert AlertPage.of([FILL], 1, 1).next is None
