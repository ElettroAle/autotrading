from dataclasses import dataclass

from autotrading.application.notifications.ports import ChannelPreferencesRepositoryPort
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent


@dataclass(frozen=True, slots=True)
class ChooseNotificationChannelCommand:
    event: NotificationEvent
    channel: NotificationChannel


class ChooseNotificationChannelUseCase:
    """Chooses the channel of a type of event for all the flows of the tenant: it counts from the next notification
    (R3.5.3).
    """

    def __init__(self, preferences: ChannelPreferencesRepositoryPort) -> None:
        self._preferences = preferences

    def execute(self, command: ChooseNotificationChannelCommand) -> None:
        chosen = self._preferences.get().choosing(command.event, command.channel)
        self._preferences.save(chosen)
