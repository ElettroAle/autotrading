"""Telegram chats named in the scenarios, numbered as Telegram would number them, the notifications they read and
where the notifications of a tenant go."""

import zlib

from autotrading.application.notifications.ports import NotificationLinkPort, NotificationRoutes
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.channel_preferences_repository import (
    ChannelPreferencesStore,
    InMemoryChannelPreferencesRepositoryAdapter,
)
from tests.fakes.notification_link import FakeNotificationLinkAdapter

# The values of a notification, one per line in the message, are written on one line of a scenario (R3.5.4).
VALUE_SEPARATOR = "; "


def chat_named(name: str) -> ChatId:
    return ChatId(zlib.crc32(name.encode()))


def notification_routes(
    tenant_id: TenantId, preferences: ChannelPreferencesStore | None = None, links: NotificationLinkPort | None = None
) -> NotificationRoutes:
    """Where the notifications of a tenant go: by default the channels of a tenant who never chose, and no dashboard
    to lead to."""
    return NotificationRoutes(
        InMemoryChannelPreferencesRepositoryAdapter({} if preferences is None else preferences, tenant_id),
        FakeNotificationLinkAdapter(dashboard=False) if links is None else links,
    )


def told(message: str, title: str, values: str) -> bool:
    """Whether the message is the notification with the title on its first line and each value on a line of its own."""
    first, *lines = message.splitlines()
    return title in first and all(value in lines for value in values.split(VALUE_SEPARATOR))


def told_in(messages: list[str], title: str, values: str) -> list[str]:
    return [message for message in messages if told(message, title, values)]
