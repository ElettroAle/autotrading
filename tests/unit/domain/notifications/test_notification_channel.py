import pytest

from autotrading.domain.notifications.notification_channel import MissingLink, NotificationChannel


def test_each_channel_is_one_of_the_four_choices_of_the_user() -> None:
    assert [channel.name for channel in NotificationChannel] == ["TELEGRAM", "EMAIL", "BOTH", "NONE"]


@pytest.mark.parametrize(
    ("channel", "chat", "email"),
    [
        (NotificationChannel.TELEGRAM, True, False),
        (NotificationChannel.EMAIL, False, True),
        (NotificationChannel.BOTH, True, True),
        (NotificationChannel.NONE, False, False),
    ],
)
def test_a_channel_says_whether_it_reaches_the_chat_and_the_email(
    channel: NotificationChannel, chat: bool, email: bool
) -> None:
    assert channel.reaches_chat is chat
    assert channel.reaches_email is email


@pytest.mark.parametrize(
    ("channel", "chat_linked", "email_indicated", "missing"),
    [
        (NotificationChannel.TELEGRAM, False, True, (MissingLink.CHAT,)),
        (NotificationChannel.TELEGRAM, True, False, ()),
        (NotificationChannel.EMAIL, True, False, (MissingLink.EMAIL,)),
        (NotificationChannel.EMAIL, False, True, ()),
        (NotificationChannel.BOTH, False, False, (MissingLink.CHAT, MissingLink.EMAIL)),
        (NotificationChannel.BOTH, True, True, ()),
        (NotificationChannel.NONE, False, False, ()),
    ],
)
def test_a_chosen_channel_not_linked_is_missing_its_link(
    channel: NotificationChannel, chat_linked: bool, email_indicated: bool, missing: tuple[MissingLink, ...]
) -> None:
    assert channel.missing_links(chat_linked=chat_linked, email_indicated=email_indicated) == missing
