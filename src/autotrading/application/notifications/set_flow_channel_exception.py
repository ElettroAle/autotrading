from dataclasses import dataclass
from uuid import UUID

from autotrading.application.notifications.errors import NotifiedFlowNotFoundError
from autotrading.application.notifications.ports import ChannelPreferencesRepositoryPort, NotifiedFlowsPort
from autotrading.domain.notifications.notification_channel import Channels
from autotrading.domain.notifications.notification_event import NotificationEvent


@dataclass(frozen=True, slots=True)
class SetFlowChannelExceptionCommand:
    flow_id: UUID
    event: NotificationEvent
    channels: Channels


class SetFlowChannelExceptionUseCase:
    """Gives a flow of the tenant channels of its own for a type of event of the flow (R3.5.3)."""

    def __init__(self, preferences: ChannelPreferencesRepositoryPort, flows: NotifiedFlowsPort) -> None:
        self._preferences = preferences
        self._flows = flows

    def execute(self, command: SetFlowChannelExceptionCommand) -> None:
        self._ensure_flow_of_tenant(command.flow_id)
        excepted = self._preferences.get().excepting(command.flow_id, command.event, command.channels)
        self._preferences.save(excepted)

    def _ensure_flow_of_tenant(self, flow_id: UUID) -> None:
        if not any(flow.flow_id == flow_id for flow in self._flows.list()):
            raise NotifiedFlowNotFoundError
