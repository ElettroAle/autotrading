from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NotificationLink:
    """A page a notification leads to, with the words its button or line shows (R3.5.6)."""

    label: str
    url: str
