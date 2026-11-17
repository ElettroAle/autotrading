from collections.abc import Iterable
from enum import StrEnum


class MissingLink(StrEnum):
    """A chosen channel with nothing to reach: the linked chat, the address of the notifications by email, or the mail
    server the emails of the tenant leave from (R3.5.5)."""

    CHAT = "chat"
    EMAIL = "email"
    MAIL_SERVER = "mail_server"


class NotificationChannel(StrEnum):
    """A channel the notifications reach (R3.5.3, RF-24.04): the linked chat or the address of the notifications by
    email. A type of event goes to a set of them, so a new channel is one member more, never new combinations (ADR
    canali-delle-notifiche-come-insieme).
    """

    TELEGRAM = "chat"
    EMAIL = "email"

    def missing_links(
        self, *, chat_linked: bool, email_indicated: bool, mail_server_configured: bool
    ) -> tuple[MissingLink, ...]:
        """What the channel misses to reach the tenant: the linked chat (R3.5.3), or the address and the mail server
        the emails leave from (R3.5.5)."""
        if self is NotificationChannel.TELEGRAM:
            return () if chat_linked else (MissingLink.CHAT,)
        missing_email = () if email_indicated else (MissingLink.EMAIL,)
        missing_server = () if mail_server_configured else (MissingLink.MAIL_SERVER,)
        return missing_email + missing_server


type Channels = frozenset[NotificationChannel]

NO_CHANNEL: Channels = frozenset()


def in_order(channels: Iterable[NotificationChannel]) -> tuple[NotificationChannel, ...]:
    """The channels of a set in the order of the channels: a set has none of its own."""
    chosen = frozenset(channels)
    return tuple(channel for channel in NotificationChannel if channel in chosen)


def missing_links_of(
    channels: Iterable[NotificationChannel], *, chat_linked: bool, email_indicated: bool, mail_server_configured: bool
) -> tuple[MissingLink, ...]:
    """What the settings warn beside an event: each chosen channel with what it misses, in the order of the channels;
    a chosen channel with nothing linked sends nothing (R3.5.3)."""
    return tuple(
        missing
        for channel in in_order(channels)
        for missing in channel.missing_links(
            chat_linked=chat_linked, email_indicated=email_indicated, mail_server_configured=mail_server_configured
        )
    )
