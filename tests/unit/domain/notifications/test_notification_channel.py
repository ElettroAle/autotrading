import pytest

from autotrading.domain.notifications.notification_channel import (
    NO_CHANNEL,
    Channels,
    MissingLink,
    NotificationChannel,
    in_order,
    missing_links_of,
)

TELEGRAM, EMAIL = NotificationChannel.TELEGRAM, NotificationChannel.EMAIL


def test_each_member_is_one_channel_never_a_combination_of_them() -> None:
    assert [channel.name for channel in NotificationChannel] == ["TELEGRAM", "EMAIL"]


def test_no_channel_is_the_empty_set() -> None:
    assert frozenset() == NO_CHANNEL


@pytest.mark.parametrize(
    ("channels", "ordered"),
    [
        (frozenset({EMAIL, TELEGRAM}), (TELEGRAM, EMAIL)),
        (frozenset({EMAIL}), (EMAIL,)),
        (NO_CHANNEL, ()),
    ],
)
def test_a_set_of_channels_reads_in_the_order_of_the_channels(
    channels: Channels, ordered: tuple[NotificationChannel, ...]
) -> None:
    assert in_order(channels) == ordered


@pytest.mark.parametrize(
    ("channel", "chat_linked", "email_indicated", "mail_server_configured", "missing"),
    [
        (TELEGRAM, False, True, True, (MissingLink.CHAT,)),
        (TELEGRAM, True, False, False, ()),
        (EMAIL, False, True, True, ()),
        (EMAIL, True, False, True, (MissingLink.EMAIL,)),
        (EMAIL, True, True, False, (MissingLink.MAIL_SERVER,)),
        (EMAIL, True, False, False, (MissingLink.EMAIL, MissingLink.MAIL_SERVER)),
    ],
)
def test_a_channel_misses_only_its_own_links(
    channel: NotificationChannel,
    chat_linked: bool,
    email_indicated: bool,
    mail_server_configured: bool,
    missing: tuple[MissingLink, ...],
) -> None:
    links = channel.missing_links(
        chat_linked=chat_linked, email_indicated=email_indicated, mail_server_configured=mail_server_configured
    )

    assert links == missing


@pytest.mark.parametrize(
    ("channels", "missing"),
    [
        (frozenset({EMAIL, TELEGRAM}), (MissingLink.CHAT, MissingLink.EMAIL, MissingLink.MAIL_SERVER)),
        (frozenset({EMAIL}), (MissingLink.EMAIL, MissingLink.MAIL_SERVER)),
        (frozenset({TELEGRAM}), (MissingLink.CHAT,)),
        (NO_CHANNEL, ()),
    ],
)
def test_a_set_of_channels_misses_the_links_of_each_of_its_channels_in_order(
    channels: Channels, missing: tuple[MissingLink, ...]
) -> None:
    links = missing_links_of(channels, chat_linked=False, email_indicated=False, mail_server_configured=False)

    assert links == missing
