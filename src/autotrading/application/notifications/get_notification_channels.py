from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.notifications.ports import (
    ChannelPreferencesRepositoryPort,
    LinkedChatRepositoryPort,
    MailServerRepositoryPort,
    NotificationEmailRepositoryPort,
    NotifiedFlowsPort,
)
from autotrading.domain.notifications.notification_channel import MissingLink, NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent


@dataclass(frozen=True, slots=True)
class EventChannel:
    """A type of event with its channel, whether a flow may have an exception for it, and the links its channel misses,
    which the settings warn beside it."""

    event: NotificationEvent
    channel: NotificationChannel
    of_flow: bool
    missing_links: tuple[MissingLink, ...]


@dataclass(frozen=True, slots=True)
class FlowChannels:
    """A flow of the tenant with its exceptions; a type of event without one follows the general choice."""

    flow_id: UUID
    name: str
    exceptions: tuple[EventChannel, ...]


@dataclass(frozen=True, slots=True)
class NotificationChannels:
    """The choices of the tenant and what it misses to reach each channel, whatever it chose (R3.5.5)."""

    events: tuple[EventChannel, ...]
    flows: tuple[FlowChannels, ...]
    missing_links: tuple[MissingLink, ...]


@dataclass(frozen=True, slots=True)
class _Links:
    """Which channels of the tenant are linked: a chosen channel without its link is warned beside the event."""

    chat_linked: bool
    email_indicated: bool
    mail_server_configured: bool

    def channels_of(self, choices: Mapping[NotificationEvent, NotificationChannel]) -> tuple[EventChannel, ...]:
        return tuple(
            EventChannel(
                event,
                channel,
                event.of_flow,
                self.missing_for(channel),
            )
            for event, channel in choices.items()
        )

    def missing_for(self, channel: NotificationChannel) -> tuple[MissingLink, ...]:
        return channel.missing_links(
            chat_linked=self.chat_linked,
            email_indicated=self.email_indicated,
            mail_server_configured=self.mail_server_configured,
        )


class GetNotificationChannelsUseCase:
    """The channel of every type of event and the exceptions of every flow of the tenant, with the warning of a
    chosen channel that is not linked (R3.5.3), and what the tenant misses to reach each channel (R3.5.5).
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
        missing = links.missing_for(NotificationChannel.BOTH)
        return NotificationChannels(links.channels_of(preferences.general_choices()), flows, missing)
