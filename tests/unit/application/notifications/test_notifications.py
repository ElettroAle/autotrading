import logging
from datetime import UTC, datetime, timedelta

import pytest

from autotrading.application.notifications.answer_bot_messages import AnswerBotMessagesUseCase
from autotrading.application.notifications.errors import (
    BotUnreachableError,
    ChatNotLinkedError,
    NoLinkedChatToTestError,
)
from autotrading.application.notifications.get_linked_chat import GetLinkedChatUseCase
from autotrading.application.notifications.link_chat import (
    HOW_TO_LINK,
    INVALID_CODE,
    LINKED,
    LinkChatCommand,
    LinkChatUseCase,
)
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.ports import BotMessage, LinkStores
from autotrading.application.notifications.request_link_code import IssuedLinkCode, RequestLinkCodeUseCase
from autotrading.application.notifications.send_linked_chat_test_notification import (
    SendLinkedChatTestNotificationUseCase,
)
from autotrading.application.notifications.send_test_notification import (
    SendTestNotificationCommand,
    SendTestNotificationUseCase,
)
from autotrading.application.notifications.unlink_chat import UnlinkChatUseCase
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.link_code import LinkCode
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.bot_identity import FakeBotIdentityAdapter
from tests.fakes.bot_inbox import FakeBotInboxAdapter
from tests.fakes.link_code_repository import (
    InMemoryLinkCodeLookupAdapter,
    InMemoryLinkCodeRepositoryAdapter,
    LinkCodeStore,
    RacedLinkCodeRepositoryAdapter,
)
from tests.fakes.linked_chat_repository import (
    InMemoryLinkedChatLookupAdapter,
    InMemoryLinkedChatRepositoryAdapter,
    LinkedChatStore,
)
from tests.fakes.messenger import FakeMessengerAdapter

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
ANNA, BRUNO = TenantId.new(), TenantId.new()
CHAT, OTHER_CHAT = ChatId(1001), ChatId(2002)
FAILED = Notification.cycle_failed("alfa", "timeout")
TEST_TEXT = "notifica di prova: le notifiche dei tuoi flussi arrivano qui"


class Telegram:
    """The stores and the bot of one test, with a clock the test moves."""

    def __init__(self) -> None:
        self.codes: LinkCodeStore = {}
        self.chats: LinkedChatStore = {}
        self.messenger = FakeMessengerAdapter()
        self.now = NOW
        self.bot = FakeBotIdentityAdapter("autotrading_bot")

    def issue_code(self, tenant_id: TenantId) -> IssuedLinkCode:
        codes = InMemoryLinkCodeRepositoryAdapter(self.codes, tenant_id)
        return RequestLinkCodeUseCase(tenant_id, codes, self.bot, lambda: self.now).execute()

    def request_code(self, tenant_id: TenantId) -> str:
        return self.issue_code(tenant_id).code

    def link_chat(self) -> LinkChatUseCase:
        return LinkChatUseCase(
            InMemoryLinkCodeLookupAdapter(self.codes), self.stores_for, self.messenger, lambda: self.now
        )

    def stores_for(self, tenant_id: TenantId) -> LinkStores:
        return LinkStores(
            InMemoryLinkCodeRepositoryAdapter(self.codes, tenant_id),
            InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id),
        )

    def send(self, chat_id: ChatId, message: str) -> None:
        self.link_chat().execute(LinkChatCommand(chat_id, message))

    def linked(self, tenant_id: TenantId) -> LinkedChat | None:
        return GetLinkedChatUseCase(InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id)).execute()

    def notify_for(self, tenant_id: TenantId) -> NotifyUseCase:
        return NotifyUseCase(InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id), self.messenger)

    def notify(self, tenant_id: TenantId, notification: Notification = FAILED) -> None:
        self.notify_for(tenant_id).execute(notification)

    def test_notification(self) -> SendTestNotificationUseCase:
        return SendTestNotificationUseCase(InMemoryLinkedChatLookupAdapter(self.chats), self.notify_for, self.messenger)

    def answering_bot(self, inbox: FakeBotInboxAdapter) -> AnswerBotMessagesUseCase:
        return AnswerBotMessagesUseCase(inbox, self.link_chat(), self.test_notification())

    def ask_for_test(self, chat_id: ChatId) -> None:
        self.test_notification().execute(SendTestNotificationCommand(chat_id))

    def ask_for_test_from_dashboard(self, tenant_id: TenantId) -> None:
        chats = InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id)
        SendLinkedChatTestNotificationUseCase(chats, self.notify_for(tenant_id)).execute()


class RecordingLinkCodeLookupAdapter(InMemoryLinkCodeLookupAdapter):
    """Records every digest looked up, to prove a message without a code reaches no tenant."""

    def __init__(self, store: LinkCodeStore) -> None:
        super().__init__(store)
        self.looked_up: list[bytes] = []

    def tenant_of(self, digest: bytes) -> TenantId | None:
        self.looked_up.append(digest)
        return super().tenant_of(digest)


@pytest.fixture
def telegram() -> Telegram:
    return Telegram()


def test_a_requested_code_is_stored_as_a_digest_valid_fifteen_minutes(telegram: Telegram) -> None:
    codes = InMemoryLinkCodeRepositoryAdapter(telegram.codes, ANNA)
    issued = RequestLinkCodeUseCase(ANNA, codes, telegram.bot, lambda: NOW).execute()

    stored = codes.get(LinkCode(issued.code).digest)
    assert stored is not None
    assert (stored.issued_at, stored.used) == (NOW, False)
    assert issued.expires_at == NOW + timedelta(minutes=15)
    assert issued.code.encode() not in b"".join(telegram.codes)
    assert issued.code not in repr(issued)


def test_a_code_comes_with_the_link_that_opens_the_bot_with_it(telegram: Telegram) -> None:
    issued = telegram.issue_code(ANNA)

    assert issued.link == f"https://t.me/autotrading_bot?start={issued.code}"


def test_without_an_active_bot_a_code_comes_without_a_link(telegram: Telegram) -> None:
    telegram.bot.name = None

    issued = telegram.issue_code(ANNA)

    assert issued.link is None
    assert len(issued.code) == 8


def test_a_valid_code_links_the_chat_that_sent_it_and_answers_it(telegram: Telegram) -> None:
    code = telegram.request_code(ANNA)
    telegram.now = NOW + timedelta(minutes=15)

    telegram.send(CHAT, f"/start {code.lower()}")

    assert telegram.linked(ANNA) == LinkedChat(ANNA, CHAT)
    assert telegram.messenger.sent == [(CHAT, LINKED)]


def test_a_code_links_only_the_tenant_that_asked_for_it(telegram: Telegram) -> None:
    code = telegram.request_code(ANNA)
    telegram.request_code(BRUNO)

    telegram.send(CHAT, code)

    assert telegram.linked(BRUNO) is None


def test_an_expired_code_links_nothing(telegram: Telegram) -> None:
    code = telegram.request_code(ANNA)
    telegram.now = NOW + timedelta(minutes=16)

    telegram.send(CHAT, code)

    assert telegram.linked(ANNA) is None
    assert telegram.messenger.sent == [(CHAT, INVALID_CODE)]


def test_a_code_links_one_chat_only(telegram: Telegram) -> None:
    code = telegram.request_code(ANNA)
    telegram.send(CHAT, code)

    telegram.send(OTHER_CHAT, code)

    assert telegram.linked(ANNA) == LinkedChat(ANNA, CHAT)
    assert telegram.messenger.sent == [(CHAT, LINKED), (OTHER_CHAT, INVALID_CODE)]


@pytest.mark.parametrize("message", ["ZZZZ9999", "/start ZZZZ9999"])
def test_an_unknown_code_gets_the_same_answer_as_an_expired_one(telegram: Telegram, message: str) -> None:
    telegram.send(CHAT, message)

    assert telegram.chats == {}
    assert telegram.messenger.sent == [(CHAT, INVALID_CODE)]


@pytest.mark.parametrize("message", ["", "/start", "/help"])
def test_a_message_without_a_code_gets_how_to_link_and_looks_nothing_up(telegram: Telegram, message: str) -> None:
    code = telegram.request_code(ANNA)
    lookup = RecordingLinkCodeLookupAdapter(telegram.codes)
    LinkChatUseCase(lookup, telegram.stores_for, telegram.messenger, lambda: NOW).execute(
        LinkChatCommand(CHAT, message)
    )

    assert lookup.looked_up == []
    assert telegram.chats == {}
    assert telegram.messenger.sent == [(CHAT, HOW_TO_LINK)]
    telegram.send(CHAT, code)
    assert telegram.linked(ANNA) == LinkedChat(ANNA, CHAT)


def test_the_start_command_with_a_valid_code_links_the_chat(telegram: Telegram) -> None:
    code = telegram.request_code(ANNA)

    telegram.send(CHAT, f"/start {code}")

    assert telegram.linked(ANNA) == LinkedChat(ANNA, CHAT)
    assert telegram.messenger.sent == [(CHAT, LINKED)]


def test_an_unknown_code_opens_the_stores_of_no_tenant(telegram: Telegram) -> None:
    opened: list[TenantId] = []

    def stores_for(tenant_id: TenantId) -> LinkStores:
        opened.append(tenant_id)
        return telegram.stores_for(tenant_id)

    lookup = InMemoryLinkCodeLookupAdapter(telegram.codes)
    LinkChatUseCase(lookup, stores_for, telegram.messenger, lambda: NOW).execute(LinkChatCommand(CHAT, "ZZZZ9999"))

    assert opened == []


def test_a_code_redeemed_meanwhile_by_another_chat_links_nothing(telegram: Telegram) -> None:
    code = telegram.request_code(ANNA)
    raced = LinkStores(
        RacedLinkCodeRepositoryAdapter(telegram.codes, ANNA), InMemoryLinkedChatRepositoryAdapter(telegram.chats, ANNA)
    )
    link_chat = LinkChatUseCase(
        InMemoryLinkCodeLookupAdapter(telegram.codes), lambda _: raced, telegram.messenger, lambda: NOW
    )

    link_chat.execute(LinkChatCommand(CHAT, code))

    assert telegram.linked(ANNA) is None
    assert telegram.messenger.sent == [(CHAT, INVALID_CODE)]


def test_a_code_of_a_lookup_without_its_link_is_refused(telegram: Telegram) -> None:
    code = telegram.request_code(ANNA)
    lookup = InMemoryLinkCodeLookupAdapter(telegram.codes)
    empty_stores = LinkStores(
        InMemoryLinkCodeRepositoryAdapter({}, ANNA), InMemoryLinkedChatRepositoryAdapter(telegram.chats, ANNA)
    )

    LinkChatUseCase(lookup, lambda _: empty_stores, telegram.messenger, lambda: NOW).execute(
        LinkChatCommand(CHAT, code)
    )

    assert telegram.messenger.sent == [(CHAT, INVALID_CODE)]
    assert telegram.chats == {}


def test_a_new_link_replaces_the_previous_chat(telegram: Telegram) -> None:
    telegram.send(CHAT, telegram.request_code(ANNA))

    telegram.send(OTHER_CHAT, telegram.request_code(ANNA))

    assert telegram.linked(ANNA) == LinkedChat(ANNA, OTHER_CHAT)


def test_an_answer_telegram_does_not_take_is_recorded_and_the_link_holds(
    telegram: Telegram, caplog: pytest.LogCaptureFixture
) -> None:
    code = telegram.request_code(ANNA)
    telegram.messenger.reachable = False

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        telegram.send(CHAT, code)

    assert telegram.linked(ANNA) == LinkedChat(ANNA, CHAT)
    assert [record.getMessage() for record in caplog.records] == ["risposta del bot non consegnata"]


def test_unlinking_removes_the_chat(telegram: Telegram) -> None:
    telegram.send(CHAT, telegram.request_code(ANNA))

    UnlinkChatUseCase(InMemoryLinkedChatRepositoryAdapter(telegram.chats, ANNA)).execute()

    assert telegram.linked(ANNA) is None


def test_unlinking_without_a_linked_chat_is_not_found(telegram: Telegram) -> None:
    with pytest.raises(ChatNotLinkedError, match=r"^nessuna chat collegata$") as raised:
        UnlinkChatUseCase(InMemoryLinkedChatRepositoryAdapter(telegram.chats, ANNA)).execute()

    assert raised.value.status_code == 404


def test_a_notification_goes_to_the_chat_of_its_tenant_only(telegram: Telegram) -> None:
    telegram.send(CHAT, telegram.request_code(ANNA))
    telegram.send(OTHER_CHAT, telegram.request_code(BRUNO))
    telegram.messenger.sent.clear()

    telegram.notify(ANNA)

    assert telegram.messenger.sent == [(CHAT, "alfa: ciclo fallito, timeout")]


def test_without_a_linked_chat_nothing_is_sent(telegram: Telegram) -> None:
    telegram.notify(ANNA)

    assert telegram.messenger.sent == []


def test_a_notification_telegram_does_not_take_is_recorded_without_failing(
    telegram: Telegram, caplog: pytest.LogCaptureFixture
) -> None:
    telegram.send(CHAT, telegram.request_code(ANNA))
    telegram.messenger.reachable = False

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        telegram.notify(ANNA)

    [record] = caplog.records
    assert record.getMessage() == "invio della notifica fallito"
    assert (record.__dict__["tenant_id"], record.__dict__["subject"]) == (str(ANNA.value), "alfa")


def test_every_message_but_the_test_command_is_a_link_attempt(telegram: Telegram) -> None:
    inbox = FakeBotInboxAdapter()
    inbox.waiting = [
        BotMessage(CHAT, telegram.request_code(ANNA)),
        BotMessage(OTHER_CHAT, "hello"),
        BotMessage(CHAT, "/prova"),
    ]

    telegram.answering_bot(inbox).execute()

    assert telegram.messenger.sent == [(CHAT, LINKED), (OTHER_CHAT, INVALID_CODE), (CHAT, TEST_TEXT)]
    assert inbox.waiting == []


def test_a_bot_round_without_telegram_fails_for_the_next_round_to_retry(telegram: Telegram) -> None:
    inbox = FakeBotInboxAdapter()
    inbox.reachable = False

    with pytest.raises(BotUnreachableError, match=r"^bot non raggiungibile$"):
        telegram.answering_bot(inbox).execute()


def test_a_linked_chat_receives_the_test_notification_by_the_road_of_the_real_ones(telegram: Telegram) -> None:
    telegram.send(CHAT, telegram.request_code(ANNA))

    telegram.ask_for_test(CHAT)

    assert telegram.messenger.received_by(CHAT) == [LINKED, TEST_TEXT]


def test_a_chat_linked_to_two_tenants_receives_one_test_notification_for_each(telegram: Telegram) -> None:
    telegram.send(CHAT, telegram.request_code(ANNA))
    telegram.send(CHAT, telegram.request_code(BRUNO))

    telegram.ask_for_test(CHAT)

    assert telegram.messenger.received_by(CHAT) == [LINKED, LINKED, TEST_TEXT, TEST_TEXT]


def test_a_chat_not_linked_asking_for_a_test_receives_how_to_link(telegram: Telegram) -> None:
    telegram.send(CHAT, telegram.request_code(ANNA))

    telegram.ask_for_test(OTHER_CHAT)

    assert telegram.messenger.received_by(OTHER_CHAT) == [HOW_TO_LINK]
    assert telegram.messenger.received_by(CHAT) == [LINKED]


def test_instructions_telegram_does_not_take_are_recorded_without_failing(
    telegram: Telegram, caplog: pytest.LogCaptureFixture
) -> None:
    telegram.messenger.reachable = False

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        telegram.ask_for_test(OTHER_CHAT)

    [record] = caplog.records
    assert record.getMessage() == "risposta del bot non consegnata"


def test_a_test_notification_telegram_does_not_take_is_recorded_like_a_real_one(
    telegram: Telegram, caplog: pytest.LogCaptureFixture
) -> None:
    telegram.send(CHAT, telegram.request_code(ANNA))
    telegram.messenger.reachable = False

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        telegram.ask_for_test(CHAT)

    [record] = caplog.records
    assert record.getMessage() == "invio della notifica fallito"
    assert record.__dict__["subject"] == "notifica di prova"


def test_a_test_from_the_dashboard_reaches_the_linked_chat_of_the_tenant_only(telegram: Telegram) -> None:
    telegram.send(CHAT, telegram.request_code(ANNA))
    telegram.send(OTHER_CHAT, telegram.request_code(BRUNO))

    telegram.ask_for_test_from_dashboard(ANNA)

    assert telegram.messenger.received_by(CHAT) == [LINKED, TEST_TEXT]
    assert telegram.messenger.received_by(OTHER_CHAT) == [LINKED]


def test_a_test_from_the_dashboard_without_a_linked_chat_is_a_conflict_and_sends_nothing(telegram: Telegram) -> None:
    telegram.send(OTHER_CHAT, telegram.request_code(BRUNO))

    with pytest.raises(NoLinkedChatToTestError, match=r"^nessuna chat collegata$") as raised:
        telegram.ask_for_test_from_dashboard(ANNA)

    assert raised.value.status_code == 409
    assert isinstance(raised.value, ChatNotLinkedError)
    assert telegram.messenger.received_by(OTHER_CHAT) == [LINKED]
