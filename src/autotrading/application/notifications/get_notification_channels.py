from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.notifications.ports import (
    ChannelPreferencesRepositoryPort,
    LinkedChatRepositoryPort,
    MailServerRepositoryPort,
    NotificationEmailRepositoryPort,
    NotifiedFlowsPort,
)
from autotrading.domain.notifications.notification_channel import (
    Channels,
    MissingLink,
    NotificationChannel,
    missing_links_of,
)
from autotrading.domain.notifications.notification_event import NotificationEvent


@dataclass(frozen=True, slots=True)
class EventChannel:
    """A type of event with its channels, whether a flow may have an exception for it, and the links its channels miss,
    which the settings warn beside it."""

    event: NotificationEvent
    channels: Channels
    of_flow: bool
    missing_links: tuple[MissingLink, ...]


@dataclass(frozen=True, slots=True)
class FlowChannels:
    """A flow of the tenant with its exceptions; a type of event without one follows the general choice."""

    flow_id: UUID
    name: str
    exceptions: tuple[EventChannel, ...]


@dataclass(frozen=True, slots=True)
class ChannelState:
    """A channel of the platform and what the tenant misses to reach it: a channel missing nothing is configured."""

    channel: NotificationChannel
    missing_links: tuple[MissingLink, ...]

    @property
    def configured(self) -> bool:
        return not self.missing_links


@dataclass(frozen=True, slots=True)
class NotificationChannels:
    """The choices of the tenant and the state of every channel, whatever it chose (R3.5.5)."""

    events: tuple[EventChannel, ...]
    flows: tuple[FlowChannels, ...]
    channels: tuple[ChannelState, ...]

    @property
    def missing_links(self) -> tuple[MissingLink, ...]:
        """What the tenant misses to reach every channel, in the order of the channels."""
        return tuple(missing for state in self.channels for missing in state.missing_links)


@dataclass(frozen=True, slots=True)
class _Links:
    """Which channels of the tenant are linked: a chosen channel without its link is warned beside the event."""

    chat_linked: bool
    email_indicated: bool
    mail_server_configured: bool

    def channels_of(self, choices: Mapping[NotificationEvent, Channels]) -> tuple[EventChannel, ...]:
        return tuple(
            EventChannel(event, channels, event.of_flow, self.missing_for(channels))
            for event, channels in choices.items()
        )

    def states(self) -> tuple[ChannelState, ...]:
        return tuple(ChannelState(channel, self.missing_for((channel,))) for channel in NotificationChannel)

    def missing_for(self, channels: Iterable[NotificationChannel]) -> tuple[MissingLink, ...]:
        return missing_links_of(
            channels,
            chat_linked=self.chat_linked,
            email_indicated=self.email_indicated,
            mail_server_configured=self.mail_server_configured,
        )


class GetNotificationChannelsUseCase:
    """The channels of every type of event and the exceptions of every flow of the tenant, with the warning of a
    chosen channel that is not linked (R3.5.3), and the state of every channel of the platform (R3.5.5, ADR
    canali-delle-notifiche-come-insieme).
    """

    def __init__(
        self,
        preferences: ChannelPreferencesRepositoryPort,
        flows: NotifiedFlowsPort,
        chats: LinkedChatRepositoryPort,
        emails: NotificationEmailRepositoryPort,
        servers: MailServerRepositoryPort,
    ) -> None:
        self._preferences = preferences
        self._flows = flows
        self._chats = chats
        self._emails = emails
        self._servers = servers

    def execute(self) -> NotificationChannels:
        preferences = self._preferences.get()
        links = _Links(
            chat_linked=self._chats.get() is not None,
            email_indicated=self._emails.get() is not None,
            mail_server_configured=self._servers.get() is not None,
        )
        flows = tuple(
            FlowChannels(flow.flow_id, flow.name, links.channels_of(preferences.exceptions_of(flow.flow_id)))
            for flow in self._flows.list()
        )
        return NotificationChannels(links.channels_of(preferences.general_choices()), flows, links.states())
