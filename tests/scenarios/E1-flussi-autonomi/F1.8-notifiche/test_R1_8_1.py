from datetime import UTC, datetime, time

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.notifications.link_chat import HOW_TO_LINK, INVALID_CODE, LINKED, LinkChatCommand
from autotrading.application.notifications.request_link_code import IssuedLinkCode
from autotrading.domain.notifications.notification import Notification
from tests.support.notifications import chat_named
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.8-notifiche/R1.8.1-collegamento-di-telegram.feature")

DAY = datetime(2026, 11, 12, tzinfo=UTC).date()


def at(clock: str) -> datetime:
    return datetime.combine(DAY, time.fromisoformat(clock), UTC)


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def codes() -> dict[str, str]:
    return {}


@pytest.fixture
def issued() -> list[IssuedLinkCode]:
    return []


def request_code(platform: Platform, user: str, codes: dict[str, str]) -> None:
    codes[user] = platform.use_cases_of(user).request_link_code.execute().code


def send_code(platform: Platform, chat: str, code: str) -> None:
    platform.link_chat().execute(LinkChatCommand(chat_named(chat), code))


def link(platform: Platform, user: str, chat: str, codes: dict[str, str]) -> None:
    request_code(platform, user, codes)
    send_code(platform, chat, codes[user])


@given(quoted('che "{user}" non ha una chat Telegram collegata'))
def no_linked_chat(platform: Platform, user: str) -> None:
    assert platform.use_cases_of(user).get_linked_chat.execute() is None


@given(quoted('che "{user}" ha chiesto un codice di collegamento alle {clock}'))
def code_requested(platform: Platform, user: str, clock: str, codes: dict[str, str]) -> None:
    platform.now = at(clock)
    request_code(platform, user, codes)


@given(quoted("che sono le {clock}"))
def clock_moves(platform: Platform, clock: str) -> None:
    platform.now = at(clock)


@given(quoted('che il codice è già stato usato dalla chat "{chat}"'))
def code_used(platform: Platform, chat: str, codes: dict[str, str]) -> None:
    send_code(platform, chat, codes["anna"])


@given(quoted('che la chat "{chat}" è collegata al tenant di "{user}"'))
def chat_linked(platform: Platform, chat: str, user: str, codes: dict[str, str]) -> None:
    link(platform, user, chat, codes)


@when(quoted('la chat "{chat}" invia il codice al bot alle {clock}'))
def chat_sends_code_at(platform: Platform, chat: str, clock: str, codes: dict[str, str]) -> None:
    platform.now = at(clock)
    send_code(platform, chat, codes["anna"])


@when(quoted('la chat "{chat}" invia il codice al bot'))
def chat_sends_code(platform: Platform, chat: str, codes: dict[str, str]) -> None:
    send_code(platform, chat, codes["anna"])


@given(quoted('che il bot della piattaforma si chiama "{username}"'))
def bot_named(platform: Platform, username: str) -> None:
    platform.bot_username = username


@given(quoted("che il bot della piattaforma non è attivo"))
def bot_inactive(platform: Platform) -> None:
    platform.bot_username = None


@when(quoted('"{user}" chiede un codice di collegamento'))
def user_requests_code(platform: Platform, user: str, issued: list[IssuedLinkCode]) -> None:
    issued.append(platform.use_cases_of(user).request_link_code.execute())


@then(quoted('insieme al codice arriva il link "{prefix}" seguito dal codice'))
def link_arrives(issued: list[IssuedLinkCode], prefix: str) -> None:
    assert issued[0].link == prefix + issued[0].code


@then(quoted("insieme al codice non arriva alcun link"))
def no_link(issued: list[IssuedLinkCode]) -> None:
    assert issued[0].link is None


@when(quoted('la chat "{chat}" invia il comando di avvio seguito dal codice alle {clock}'))
def chat_starts_with_code(platform: Platform, chat: str, clock: str, codes: dict[str, str]) -> None:
    platform.now = at(clock)
    send_code(platform, chat, f"/start {codes['anna']}")


@when(quoted('la chat "{chat}" invia "{message}" al bot'))
def chat_sends_message(platform: Platform, chat: str, message: str) -> None:
    send_code(platform, chat, message)


@when(quoted('"{user}" collega la chat "{chat}"'))
def user_links(platform: Platform, user: str, chat: str, codes: dict[str, str]) -> None:
    link(platform, user, chat, codes)


@when(quoted('"{user}" scollega la chat Telegram'))
def user_unlinks(platform: Platform, user: str) -> None:
    platform.use_cases_of(user).unlink_chat.execute()


@then(quoted('la chat "{chat}" è collegata al tenant di "{user}"'))
def is_linked(platform: Platform, chat: str, user: str) -> None:
    linked = platform.use_cases_of(user).get_linked_chat.execute()
    assert linked is not None
    assert linked.chat_id == chat_named(chat)


@then(quoted('il bot risponde alla chat "{chat}" che il collegamento è riuscito'))
def answered_linked(platform: Platform, chat: str) -> None:
    assert platform.messenger.received_by(chat_named(chat)) == [LINKED]


@then(quoted('la chat "{chat}" non è collegata ad alcun tenant'))
def linked_nowhere(platform: Platform, chat: str) -> None:
    assert chat_named(chat) not in [linked.chat_id for linked in platform.chats.values()]


@then(quoted('il bot risponde alla chat "{chat}" "{answer}"'))
def answered(platform: Platform, chat: str, answer: str) -> None:
    assert answer == INVALID_CODE
    assert platform.messenger.received_by(chat_named(chat)) == [answer]


@then(quoted('il bot risponde alla chat "{chat}" con le istruzioni per il collegamento'))
def answered_how_to_link(platform: Platform, chat: str) -> None:
    assert platform.messenger.received_by(chat_named(chat)) == [HOW_TO_LINK]


@then(quoted('la chat "{chat}" non riceve più le notifiche di "{user}"'))
def no_more_notifications(platform: Platform, chat: str, user: str) -> None:
    before = len(platform.messenger.received_by(chat_named(chat)))

    platform.worker_for(platform.tenant_of(user)).notify.execute(Notification.cycle_failed("alfa", "timeout"))

    assert len(platform.messenger.received_by(chat_named(chat))) == before
