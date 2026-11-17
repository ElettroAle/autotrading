"""Telegram chats named in the scenarios, numbered as Telegram would number them, and the notifications they read."""

import zlib

from autotrading.domain.notifications.chat_id import ChatId

# The values of a notification, one per line in the message, are written on one line of a scenario (R3.5.4).
VALUE_SEPARATOR = "; "


def chat_named(name: str) -> ChatId:
    return ChatId(zlib.crc32(name.encode()))


def told(message: str, title: str, values: str) -> bool:
    """Whether the message is the notification with the title on its first line and each value on a line of its own."""
    first, *lines = message.splitlines()
    return title in first and all(value in lines for value in values.split(VALUE_SEPARATOR))


def told_in(messages: list[str], title: str, values: str) -> list[str]:
    return [message for message in messages if told(message, title, values)]
