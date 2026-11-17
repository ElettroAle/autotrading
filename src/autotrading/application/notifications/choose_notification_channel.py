from dataclasses import dataclass

from autotrading.application.notifications.ports import ChannelPreferencesRepositoryPort
from autotrading.domain.notifications.notification_channel import Channels
from autotrading.domain.notifications.notification_event import NotificationEvent


@dataclass(frozen=True, slots=True)
class ChooseNotificationChannelCommand:
    event: NotificationEvent
    channels: Channels


class ChooseNotificationChannelUseCase:
    """Chooses the channels of a type of event for all the flows of the tenant: it counts from the next notification
    (R3.5.3).
    """

    def __init__(self, preferences: ChannelPreferencesRepositoryPort) -> None:
        self._preferences = preferences

    def execute(self, command: ChooseNotificationChannelCommand) -> None:
        chosen = self._preferences.get().choosing(command.event, command.channels)
        self._preferences.save(chosen)
