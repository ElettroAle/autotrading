from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChatId:
    """The Telegram chat a tenant receives its notifications in, as Telegram numbers it (R1.8.1)."""

    value: int
