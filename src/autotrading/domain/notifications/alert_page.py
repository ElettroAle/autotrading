from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from autotrading.domain.notifications.alert import Alert, AlertResourceKind, AlertSeverity, AlertState

ALERT_PAGE_SIZE = 50
# An alert resolved more than this ago is forgotten (R6.2.3).
RESOLVED_ALERT_RETENTION = timedelta(days=90)


@dataclass(frozen=True, slots=True, order=True)
class AlertCursor:
    """The place of an alert in the list, newest first: its opening, then its id (ADR 0074)."""

    opened_at: datetime
    alert_id: UUID

    @classmethod
    def of(cls, alert: Alert) -> AlertCursor:
        return cls(alert.opened_at, alert.id.value)


@dataclass(frozen=True, slots=True)
class AlertFilter:
    """What the user asks of the alerts: a state, a severity, a kind of resource or one resource, and a period of
    opening from `since` included to `until` excluded. A missing value does not narrow.
    """

    state: AlertState | None = None
    severity: AlertSeverity | None = None
    resource_kind: AlertResourceKind | None = None
    resource_id: UUID | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = ALERT_PAGE_SIZE

    def admits(self, alert: Alert, after: AlertCursor | None = None) -> bool:
        resource = alert.cause.resource
        return (
            (self.state is None or alert.state is self.state)
            and (self.severity is None or alert.severity is self.severity)
            and (self.resource_kind is None or resource.kind is self.resource_kind)
            and (self.resource_id is None or resource.resource_id == self.resource_id)
            and (self.since is None or alert.opened_at >= self.since)
            and (self.until is None or alert.opened_at < self.until)
            and (after is None or AlertCursor.of(alert) < after)
        )


@dataclass(frozen=True, slots=True)
class AlertPage:
    """A page of alerts, newest first, where the next page starts if there is one, and how many alerts the filter
    admits in all."""

    alerts: tuple[Alert, ...]
    next: AlertCursor | None
    count: int

    @classmethod
    def of(cls, newest_first: Sequence[Alert], limit: int, count: int) -> AlertPage:
        """The page from up to one alert more than the limit: that extra alert says another page follows."""
        page = tuple(newest_first[:limit])
        more = len(newest_first) > limit
        return cls(page, AlertCursor.of(page[-1]) if more and page else None, count)
