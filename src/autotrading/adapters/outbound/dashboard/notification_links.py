from collections.abc import Callable
from datetime import UTC
from urllib.parse import quote, urlencode

from autotrading.domain.notifications.notification_link import NotificationLink
from autotrading.domain.notifications.notification_target import NotificationTarget, TargetKind


class DashboardNotificationLinkAdapter:
    """The pages of the dashboard a notification leads to, on the address the installation declares for it (ADR
    destinazioni-delle-notifiche-nella-dashboard, ADR 0117): the only place that knows the routes of the dashboard.

    Without an address no target leads anywhere, and the notifications leave without links.
    """

    def __init__(self, url: str | None) -> None:
        self._url = url

    def link(self, target: NotificationTarget) -> NotificationLink | None:
        if self._url is None:
            return None
        return NotificationLink(target.label, f"{self._url}{_ROUTES[target.kind](target)}")


def _flow(target: NotificationTarget) -> str:
    return f"/flows/{quote(str(target.owner_id))}"


def _open_position(target: NotificationTarget) -> str:
    return f"{_flow(target)}/positions?{urlencode({'asset': target.asset or ''})}"


def _closed_position(target: NotificationTarget) -> str:
    # The instant in UTC, as the history of the positions gives it: the dashboard finds the row by it.
    closed_at = "" if target.closed_at is None else target.closed_at.astimezone(UTC).isoformat()
    return f"{_flow(target)}/closed-positions?{urlencode({'asset': target.asset or '', 'closed_at': closed_at})}"


def _account_alarms(target: NotificationTarget) -> str:
    return f"/accounts/{quote(str(target.owner_id))}/alarms"


_ROUTES: dict[TargetKind, Callable[[NotificationTarget], str]] = {
    TargetKind.FLOW: _flow,
    TargetKind.OPEN_POSITION: _open_position,
    TargetKind.CLOSED_POSITION: _closed_position,
    TargetKind.ACCOUNT_ALARMS: _account_alarms,
}
