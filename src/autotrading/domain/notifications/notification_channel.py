from enum import StrEnum


class MissingLink(StrEnum):
    """A chosen channel with nothing to reach: the linked chat or the address of the notifications by email."""

    CHAT = "chat"
    EMAIL = "email"


class NotificationChannel(StrEnum):
    """Where the notifications of a type of event go (R3.5.3, RF-24.04): the linked chat, the address of the
    notifications by email, both or neither. The words the user chooses them by are those of the interface.
    """

    TELEGRAM = "chat"
    EMAIL = "email"
    BOTH = "both"
    NONE = "none"

    @property
    def reaches_chat(self) -> bool:
        return self in {NotificationChannel.TELEGRAM, NotificationChannel.BOTH}

    @property
    def reaches_email(self) -> bool:
        return self in {NotificationChannel.EMAIL, NotificationChannel.BOTH}

    def missing_links(self, *, chat_linked: bool, email_indicated: bool) -> tuple[MissingLink, ...]:
        """What the settings warn beside the event: a chosen channel with nothing linked sends nothing (R3.5.3)."""
        missing_chat = (MissingLink.CHAT,) if self.reaches_chat and not chat_linked else ()
        missing_email = (MissingLink.EMAIL,) if self.reaches_email and not email_indicated else ()
        return missing_chat + missing_email
