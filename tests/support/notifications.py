"""Telegram chats named in the scenarios, numbered as Telegram would number them, and the channels chosen by a
tenant."""

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
