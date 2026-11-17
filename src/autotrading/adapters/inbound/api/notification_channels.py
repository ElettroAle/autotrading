from collections.abc import Callable, Iterable
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.notifications.choose_notification_channel import ChooseNotificationChannelCommand
from autotrading.application.notifications.get_notification_channels import (
    ChannelState,
    EventChannel,
    FlowChannels,
    NotificationChannels,
)
from autotrading.application.notifications.remove_flow_channel_exception import RemoveFlowChannelExceptionCommand
from autotrading.application.notifications.set_flow_channel_exception import SetFlowChannelExceptionCommand
from autotrading.domain.notifications.notification_channel import Channels, MissingLink, NotificationChannel, in_order
from autotrading.domain.notifications.notification_event import NotificationEvent

# The words the user chooses the channels by, and those of the warnings, are the interface's: the core names no
# messaging service (R3.5.3). A type of event goes to a list of them, empty for none (ADR
# canali-delle-notifiche-come-insieme).
type ChannelName = Literal["Telegram", "email"]
CHANNEL_NAMES: dict[NotificationChannel, ChannelName] = {
    NotificationChannel.TELEGRAM: "Telegram",
    NotificationChannel.EMAIL: "email",
}
_CHANNELS_BY_NAME = {name: channel for channel, name in CHANNEL_NAMES.items()}
WARNINGS = {
    MissingLink.CHAT: "Telegram non collegato",
    MissingLink.EMAIL: "email non indicata",
    MissingLink.MAIL_SERVER: "server di posta non configurato",
}


def channels_named(names: Iterable[ChannelName]) -> Channels:
    return frozenset(_CHANNELS_BY_NAME[name] for name in names)


def names_of(channels: Channels) -> list[ChannelName]:
    return [CHANNEL_NAMES[channel] for channel in in_order(channels)]


def warning_of(missing: MissingLink) -> str:
    return WARNINGS[missing]


def warnings_of(missing_links: Iterable[MissingLink]) -> list[str]:
    return [warning_of(missing) for missing in missing_links]


class EventChannelResponse(BaseModel):
    """A type of event by the name the user reads, its channels, whether a flow may have an exception for it, and
    the warnings of a chosen channel that is not linked (R3.5.3)."""

    event: NotificationEvent
    channels: list[ChannelName]
    of_flow: bool
    warnings: list[str]

    @classmethod
    def of(cls, channel: EventChannel) -> EventChannelResponse:
        return cls(
            event=channel.event,
            channels=names_of(channel.channels),
            of_flow=channel.of_flow,
            warnings=warnings_of(channel.missing_links),
        )


class FlowChannelsResponse(BaseModel):
    """A flow of the tenant with its exceptions; an event without one follows the general choice."""

    flow_id: UUID
    name: str
    exceptions: list[EventChannelResponse]

    @classmethod
    def of(cls, flow: FlowChannels) -> FlowChannelsResponse:
        exceptions = [EventChannelResponse.of(channel) for channel in flow.exceptions]
        return cls(flow_id=flow.flow_id, name=flow.name, exceptions=exceptions)


class ChannelStateResponse(BaseModel):
    """A channel of the platform, whether the user configured it, and otherwise what it misses (R3.5.5)."""

    channel: ChannelName
    configured: bool
    warnings: list[str]

    @classmethod
    def of(cls, state: ChannelState) -> ChannelStateResponse:
        return cls(
            channel=CHANNEL_NAMES[state.channel], configured=state.configured, warnings=warnings_of(state.missing_links)
        )


class NotificationChannelsResponse(BaseModel):
    """The choices of the user, every channel with its state and, whatever the choices, the warning of every channel
    that cannot be reached (R3.5.5)."""

    events: list[EventChannelResponse]
    flows: list[FlowChannelsResponse]
    channels: list[ChannelStateResponse]
    warnings: list[str]

    @classmethod
    def of(cls, channels: NotificationChannels) -> NotificationChannelsResponse:
        return cls(
            events=[EventChannelResponse.of(channel) for channel in channels.events],
            flows=[FlowChannelsResponse.of(flow) for flow in channels.flows],
            channels=[ChannelStateResponse.of(state) for state in channels.channels],
            warnings=warnings_of(channels.missing_links),
        )


class ChannelChoiceRequest(BaseModel):
    """The channels of a type of event for all the flows of the user, none for no notification."""

    event: NotificationEvent
    channels: list[ChannelName]


class FlowChannelRequest(BaseModel):
    """The channels of a flow for the type of event of the path, none for no notification."""

    channels: list[ChannelName]


def notification_channels_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/notifications/channels", tags=["canali delle notifiche"])

    @router.get("")
    def read_notification_channels(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> NotificationChannelsResponse:
        return NotificationChannelsResponse.of(use_cases.get_notification_channels.execute())

    @router.put("", status_code=status.HTTP_204_NO_CONTENT)
    def choose_notification_channel(
        request: ChannelChoiceRequest, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> None:
        use_cases.choose_notification_channel.execute(
            ChooseNotificationChannelCommand(request.event, channels_named(request.channels))
        )

    @router.put("/flows/{flow_id}/{event}", status_code=status.HTTP_204_NO_CONTENT)
    def set_flow_channel_exception(
        flow_id: UUID,
        event: NotificationEvent,
        request: FlowChannelRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> None:
        command = SetFlowChannelExceptionCommand(flow_id, event, channels_named(request.channels))
        use_cases.set_flow_channel_exception.execute(command)

    @router.delete("/flows/{flow_id}/{event}", status_code=status.HTTP_204_NO_CONTENT)
    def remove_flow_channel_exception(
        flow_id: UUID, event: NotificationEvent, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> None:
        use_cases.remove_flow_channel_exception.execute(RemoveFlowChannelExceptionCommand(flow_id, event))

    return router
