from autotrading.domain.notifications.notification_link import NotificationLink
from autotrading.domain.notifications.notification_target import NotificationTarget


class FakeNotificationLinkAdapter:
    """The pages of a dashboard as the tests see them: every target has an address of its own that names what finds
    it, or no page at all when the installation names no dashboard."""

    def __init__(self, *, dashboard: bool = True) -> None:
        self.dashboard = dashboard

    def link(self, target: NotificationTarget) -> NotificationLink | None:
        if not self.dashboard:
            return None
        return NotificationLink(target.label, self.address_of(target))

    @staticmethod
    def address_of(target: NotificationTarget) -> str:
        closed_at = "" if target.closed_at is None else target.closed_at.isoformat()
        return f"dashboard:{target.kind.value}/{target.owner_id}/{target.asset or ''}/{closed_at}"
