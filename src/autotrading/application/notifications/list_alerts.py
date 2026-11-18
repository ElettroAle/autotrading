from dataclasses import dataclass

from autotrading.application.notifications.ports import AlertRepositoryPort
from autotrading.domain.notifications.alert_page import AlertCursor, AlertFilter, AlertPage


@dataclass(frozen=True, slots=True)
class ListAlertsCommand:
    criteria: AlertFilter
    after: AlertCursor | None = None


class ListAlertsUseCase:
    """The alerts of the tenant the filter admits, newest first, by pages (R6.2.3, ADR 0074)."""

    def __init__(self, alerts: AlertRepositoryPort) -> None:
        self._alerts = alerts

    def execute(self, command: ListAlertsCommand) -> AlertPage:
        return self._alerts.list(command.criteria, command.after)
