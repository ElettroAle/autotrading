"""Telegram chats named in the scenarios, numbered as Telegram would number them, the notifications they read and
the channels chosen by a tenant."""

import zlib

from autotrading.application.notifications.ports import ChannelChoicePorts
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.channel_preferences_repository import (
    ChannelPreferencesStore,
    InMemoryChannelPreferencesRepositoryAdapter,
)
from tests.fakes.flow_repository import FlowStore
from tests.fakes.notified_flows import InMemoryNotifiedFlowsAdapter

# The values of a notification, one per line in the message, are written on one line of a scenario (R3.5.4).
VALUE_SEPARATOR = "; "


def chat_named(name: str) -> ChatId:
    return ChatId(zlib.crc32(name.encode()))


def channel_choices(
    tenant_id: TenantId, preferences: ChannelPreferencesStore | None = None, flows: FlowStore | None = None
) -> ChannelChoicePorts:
    """The choices of the channels of a tenant: by default those of a tenant who never chose, without flows."""
    return ChannelChoicePorts(
        InMemoryChannelPreferencesRepositoryAdapter({} if preferences is None else preferences, tenant_id),
        InMemoryNotifiedFlowsAdapter(FlowStore() if flows is None else flows, tenant_id),
    )


def told(message: str, title: str, values: str) -> bool:
    """Whether the message is the notification with the title on its first line and each value on a line of its own."""
    first, *lines = message.splitlines()
    return title in first and all(value in lines for value in values.split(VALUE_SEPARATOR))


def told_in(messages: list[str], title: str, values: str) -> list[str]:
    return [message for message in messages if told(message, title, values)]
