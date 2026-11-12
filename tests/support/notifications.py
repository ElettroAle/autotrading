"""Telegram chats named in the scenarios, numbered as Telegram would number them."""

import zlib

from autotrading.domain.notifications.chat_id import ChatId


def chat_named(name: str) -> ChatId:
    return ChatId(zlib.crc32(name.encode()))
