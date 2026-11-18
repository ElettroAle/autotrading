from dataclasses import dataclass

from autotrading.application.notifications.ports import AlertRepositoryPort
from autotrading.domain.notifications.alert import AlertId


@dataclass(frozen=True, slots=True)
class ResolveAlertCommand:
    alert_id: AlertId


class ResolveAlertUseCase:
    """The user resolves an alert that has no resolution of its own; one that resolves when its cause goes stays open
    (R6.2.3).
    """

    def __init__(self, alerts: AlertRepositoryPort) -> None:
        self._alerts = alerts

    def execute(self, command: ResolveAlertCommand) -> None:
        self._alerts.get(command.alert_id).require_resolvable_by_hand()
        self._alerts.resolve(command.alert_id)
