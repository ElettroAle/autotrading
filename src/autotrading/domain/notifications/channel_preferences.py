from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import UUID

from autotrading.domain.notifications.errors import AccountEventWithoutFlowExceptionError
from autotrading.domain.notifications.notification_channel import NO_CHANNEL, Channels, NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

type Choices = Mapping[NotificationEvent, Channels]

# Until the user chooses, the decisions the risk check changes stay silent: they come at every cycle (R3.5.3).
_SILENT_BY_DEFAULT = frozenset({NotificationEvent.OPENING_REDUCED, NotificationEvent.OPENING_BLOCKED})


def default_channels(event: NotificationEvent) -> Channels:
    return NO_CHANNEL if event in _SILENT_BY_DEFAULT else frozenset({NotificationChannel.TELEGRAM})


@dataclass(frozen=True, slots=True)
class ChannelPreferences(TenantOwned):
    """The channels the user chose for each type of event, for all their flows, and the exceptions of single flows
    (R3.5.3, RF-24.04): a set of channels, empty when the event reaches nobody; an event without a choice goes to its
    default channels (ADR canali-delle-notifiche-come-insieme).
    """

    tenant_id: TenantId
    choices: Choices = field(default_factory=dict)
    exceptions: Mapping[UUID, Choices] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "choices", MappingProxyType(dict(self.choices)))
        frozen = {flow_id: MappingProxyType(dict(choices)) for flow_id, choices in self.exceptions.items()}
        object.__setattr__(self, "exceptions", MappingProxyType(frozen))

    @classmethod
    def of(cls, tenant_id: TenantId) -> ChannelPreferences:
        """The preferences of a tenant who never chose: every event on its default channels."""
        return cls(tenant_id)

    def channels_for(self, event: NotificationEvent, flow_id: UUID | None) -> Channels:
        """The exception of the flow, else the general choice, else the default of the event."""
        excepted = self.exceptions_of(flow_id).get(event) if flow_id is not None else None
        if excepted is not None:
            return excepted
        return self.choices.get(event, default_channels(event))

    def general_choices(self) -> Choices:
        """Every type of event, in its order, with the channels that count for all the flows."""
        return {event: self.choices.get(event, default_channels(event)) for event in NotificationEvent}

    def exceptions_of(self, flow_id: UUID) -> Choices:
        return self.exceptions.get(flow_id, {})

    def flows_with_exceptions(self) -> tuple[UUID, ...]:
        return tuple(self.exceptions)

    def choosing(self, event: NotificationEvent, channels: Channels) -> ChannelPreferences:
        return ChannelPreferences(self.tenant_id, {**self.choices, event: channels}, self.exceptions)

    def excepting(self, flow_id: UUID, event: NotificationEvent, channels: Channels) -> ChannelPreferences:
        """Channels of the flow other than the general ones; an event of the account follows the general ones only."""
        if not event.of_flow:
            raise AccountEventWithoutFlowExceptionError(event.value)
        excepted = {**self.exceptions_of(flow_id), event: channels}
        return ChannelPreferences(self.tenant_id, self.choices, {**self.exceptions, flow_id: excepted})

    def without_exception(self, flow_id: UUID, event: NotificationEvent) -> ChannelPreferences:
        """The flow back to the general choice for the event; a flow left without exceptions is forgotten."""
        remaining = {each: channels for each, channels in self.exceptions_of(flow_id).items() if each is not event}
        others = {each: choices for each, choices in self.exceptions.items() if each != flow_id}
        exceptions = {**others, flow_id: remaining} if remaining else others
        return ChannelPreferences(self.tenant_id, self.choices, exceptions)
