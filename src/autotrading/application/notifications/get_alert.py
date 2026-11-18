from dataclasses import dataclass

from autotrading.application.notifications.ports import AlertRepositoryPort
from autotrading.domain.notifications.alert import Alert, AlertId


@dataclass(frozen=True, slots=True)
class GetAlertCommand:
    alert_id: AlertId


class GetAlertUseCase:
    """An alert of the tenant with what happened and the commands that resolve it (R6.2.3)."""

    def __init__(self, alerts: AlertRepositoryPort) -> None:
        self._alerts = alerts

    def execute(self, command: GetAlertCommand) -> Alert:
        return self._alerts.get(command.alert_id)
