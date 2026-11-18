from autotrading.application.notifications.ports import AlertRepositoryPort


class CountOpenAlertsUseCase:
    """How many alerts of the tenant are open: the number of the menu (R6.2.3)."""

    def __init__(self, alerts: AlertRepositoryPort) -> None:
        self._alerts = alerts

    def execute(self) -> int:
        return self._alerts.open_count()
