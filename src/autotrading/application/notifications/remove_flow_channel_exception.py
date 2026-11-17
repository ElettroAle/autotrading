from dataclasses import dataclass
from uuid import UUID

from autotrading.application.notifications.ports import ChannelPreferencesRepositoryPort
from autotrading.domain.notifications.notification_event import NotificationEvent


@dataclass(frozen=True, slots=True)
class RemoveFlowChannelExceptionCommand:
    flow_id: UUID
    event: NotificationEvent


class RemoveFlowChannelExceptionUseCase:
    """Takes away the exception of a flow, which follows the general choice again; nothing to take away is no error
    (R3.5.3).
    """

    def __init__(self, preferences: ChannelPreferencesRepositoryPort) -> None:
        self._preferences = preferences

    def execute(self, command: RemoveFlowChannelExceptionCommand) -> None:
        removed = self._preferences.get().without_exception(command.flow_id, command.event)
        self._preferences.save(removed)
