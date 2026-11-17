"""The channel of every type of event with the exceptions of a flow, and the notifications queued only on it (R3.5.3,
ADR canali-delle-notifiche-per-tipo-di-evento).
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.notifications.choose_notification_channel import (
    ChooseNotificationChannelCommand,
    ChooseNotificationChannelUseCase,
)
from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.application.notifications.errors import NotifiedFlowNotFoundError
from autotrading.application.notifications.get_notification_channels import (
    EventChannel,
    FlowChannels,
    GetNotificationChannelsUseCase,
    NotificationChannels,
)
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.ports import ChannelChoicePorts, NotifiedFlow
from autotrading.application.notifications.remove_flow_channel_exception import (
    RemoveFlowChannelExceptionCommand,
    RemoveFlowChannelExceptionUseCase,
)
from autotrading.application.notifications.set_flow_channel_exception import (
    SetFlowChannelExceptionCommand,
    SetFlowChannelExceptionUseCase,
)
from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.errors import AccountEventWithoutFlowExceptionError
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Amount, Notification
from autotrading.domain.notifications.notification_channel import MissingLink, NotificationChannel
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.channel_preferences_repository import (
    ChannelPreferencesStore,
    InMemoryChannelPreferencesRepositoryAdapter,
)
from tests.fakes.linked_chat_repository import InMemoryLinkedChatRepositoryAdapter, LinkedChatStore
from tests.fakes.mailer import FakeMailerAdapter
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.notification_email_repository import (
    InMemoryNotificationEmailRepositoryAdapter,
    NotificationEmailStore,
)
from tests.fakes.outbox import InMemoryOutboxAdapter
from tests.support.mail_servers import MailServers

ANNA, BRUNO = TenantId.new(), TenantId.new()
ALFA, BETA = NotifiedFlow(uuid4(), "alfa"), NotifiedFlow(uuid4(), "beta")
CHAT = ChatId(42)
ADDRESS = EmailAddress.parse("anna@example.com")
FAILED_ALFA = Notification.cycle_failed("alfa", "modello non raggiungibile")
FAILED_BETA = Notification.cycle_failed("beta", "modello non raggiungibile")
ALARM = Notification.reconciliation_alarm("test-1", Amount(Decimal(980), "USDC"), Amount(Decimal(1000), "USDC"))


class FixedNotifiedFlowsAdapter:
    def __init__(self, *flows: NotifiedFlow) -> None:
        self.flows = flows

    def list(self) -> tuple[NotifiedFlow, ...]:
        return self.flows


class Channels:
    """The chats, addresses and choices of every tenant of one test; the outbox delivers at once."""

    def __init__(self) -> None:
        self.preferences: ChannelPreferencesStore = {}
        self.chats: LinkedChatStore = {ANNA: LinkedChat(ANNA, CHAT)}
        self.emails: NotificationEmailStore = {ANNA: NotificationEmail(ANNA, ADDRESS)}
        self.flows = FixedNotifiedFlowsAdapter(ALFA, BETA)
        self.servers = MailServers()
        self.servers.configure(ANNA, ADDRESS.value)
        self.messenger = FakeMessengerAdapter()
        self.mailer = FakeMailerAdapter()
        self.outbox = InMemoryOutboxAdapter()
        self.outbox.process(DeliverOutboxMessageUseCase(self.messenger, self.mailer, self.servers.access_of).execute)

    def repository(self, tenant_id: TenantId = ANNA) -> InMemoryChannelPreferencesRepositoryAdapter:
        return InMemoryChannelPreferencesRepositoryAdapter(self.preferences, tenant_id)

    def choose(self, event: NotificationEvent, channel: NotificationChannel, tenant_id: TenantId = ANNA) -> None:
        command = ChooseNotificationChannelCommand(event, channel)
        ChooseNotificationChannelUseCase(self.repository(tenant_id)).execute(command)

    def except_flow(self, flow: NotifiedFlow, event: NotificationEvent, channel: NotificationChannel) -> None:
        command = SetFlowChannelExceptionCommand(flow.flow_id, event, channel)
        SetFlowChannelExceptionUseCase(self.repository(), self.flows).execute(command)

    def remove_exception(self, flow: NotifiedFlow, event: NotificationEvent) -> None:
        command = RemoveFlowChannelExceptionCommand(flow.flow_id, event)
        RemoveFlowChannelExceptionUseCase(self.repository()).execute(command)

    def read(self, tenant_id: TenantId = ANNA) -> NotificationChannels:
        return GetNotificationChannelsUseCase(
            self.repository(tenant_id),
            self.flows,
            InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id),
            InMemoryNotificationEmailRepositoryAdapter(self.emails, tenant_id),
            self.servers.repository(tenant_id),
        ).execute()

    def notify(self, notification: Notification, tenant_id: TenantId = ANNA) -> None:
        NotifyUseCase(
            InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id),
            InMemoryNotificationEmailRepositoryAdapter(self.emails, tenant_id),
            self.servers.repository(tenant_id),
            self.outbox,
            ChannelChoicePorts(self.repository(tenant_id), self.flows),
        ).execute(notification)

    def chat_texts(self) -> list[str]:
        return self.messenger.received_by(CHAT)

    def email_texts(self) -> list[str]:
        return [email.text for email in self.mailer.received_by(ADDRESS.value)]


@pytest.fixture
def channels() -> Channels:
    return Channels()


def test_a_tenant_who_never_chose_reads_the_default_channels_and_the_flows(channels: Channels) -> None:
    read = channels.read()

    assert read.events[0] == EventChannel(NotificationEvent.POSITION_OPENED, NotificationChannel.TELEGRAM, True, ())
    assert [each.event for each in read.events] == list(NotificationEvent)
    reduced = next(each for each in read.events if each.event is NotificationEvent.OPENING_REDUCED)
    assert reduced.channel is NotificationChannel.NONE
    alarm = next(each for each in read.events if each.event is NotificationEvent.RECONCILIATION_ALARM)
    assert alarm.of_flow is False
    assert read.flows == (FlowChannels(ALFA.flow_id, "alfa", ()), FlowChannels(BETA.flow_id, "beta", ()))


def test_a_chosen_channel_is_read_back_and_counts_for_that_tenant_only(channels: Channels) -> None:
    channels.choose(NotificationEvent.CYCLE_FAILED, NotificationChannel.BOTH)

    failed = next(each for each in channels.read().events if each.event is NotificationEvent.CYCLE_FAILED)
    assert failed.channel is NotificationChannel.BOTH
    bruno = next(each for each in channels.read(BRUNO).events if each.event is NotificationEvent.CYCLE_FAILED)
    assert bruno.channel is NotificationChannel.TELEGRAM


def test_a_channel_without_its_link_is_warned_beside_the_event(channels: Channels) -> None:
    channels.chats.clear()
    channels.emails.clear()
    channels.choose(NotificationEvent.CYCLE_FAILED, NotificationChannel.BOTH)
    channels.except_flow(ALFA, NotificationEvent.POSITION_OPENED, NotificationChannel.EMAIL)

    read = channels.read()

    failed = next(each for each in read.events if each.event is NotificationEvent.CYCLE_FAILED)
    assert failed.missing_links == (MissingLink.CHAT, MissingLink.EMAIL)
    [alfa, _] = read.flows
    assert alfa.exceptions == (
        EventChannel(NotificationEvent.POSITION_OPENED, NotificationChannel.EMAIL, True, (MissingLink.EMAIL,)),
    )


def test_a_tenant_with_every_channel_linked_misses_nothing(channels: Channels) -> None:
    assert channels.read().missing_links == ()


def test_the_channels_tell_what_the_tenant_misses_whatever_the_choices(channels: Channels) -> None:
    channels.chats.clear()
    channels.servers.store.clear()

    assert channels.read().missing_links == (MissingLink.CHAT, MissingLink.MAIL_SERVER)


def test_an_email_chosen_without_a_mail_server_is_warned_beside_the_event(channels: Channels) -> None:
    channels.servers.store.clear()
    channels.choose(NotificationEvent.CYCLE_FAILED, NotificationChannel.EMAIL)

    failed = next(each for each in channels.read().events if each.event is NotificationEvent.CYCLE_FAILED)

    assert failed.missing_links == (MissingLink.MAIL_SERVER,)


def test_without_a_mail_server_no_notification_goes_by_email(channels: Channels) -> None:
    channels.servers.store.clear()
    channels.choose(NotificationEvent.CYCLE_FAILED, NotificationChannel.BOTH)

    channels.notify(FAILED_ALFA)

    assert channels.email_texts() == []
    assert channels.chat_texts() == [FAILED_ALFA.text]


def test_the_exception_of_a_flow_is_read_with_the_flow(channels: Channels) -> None:
    channels.except_flow(BETA, NotificationEvent.CYCLE_FAILED, NotificationChannel.NONE)

    [alfa, beta] = channels.read().flows

    assert alfa.exceptions == ()
    assert beta.exceptions == (EventChannel(NotificationEvent.CYCLE_FAILED, NotificationChannel.NONE, True, ()),)


def test_an_exception_for_a_flow_the_tenant_lacks_is_refused(channels: Channels) -> None:
    with pytest.raises(NotifiedFlowNotFoundError):
        channels.except_flow(NotifiedFlow(uuid4(), "gamma"), NotificationEvent.CYCLE_FAILED, NotificationChannel.NONE)

    assert channels.preferences == {}


def test_an_exception_for_an_event_of_the_account_is_refused(channels: Channels) -> None:
    with pytest.raises(AccountEventWithoutFlowExceptionError):
        channels.except_flow(ALFA, NotificationEvent.RECONCILIATION_ALARM, NotificationChannel.NONE)

    assert channels.preferences == {}


def test_a_removed_exception_leaves_the_flow_to_the_general_choice(channels: Channels) -> None:
    channels.except_flow(ALFA, NotificationEvent.CYCLE_FAILED, NotificationChannel.NONE)

    channels.remove_exception(ALFA, NotificationEvent.CYCLE_FAILED)

    assert channels.preferences[ANNA] == ChannelPreferences.of(ANNA)


@pytest.mark.parametrize(
    ("channel", "chat", "email"),
    [
        (NotificationChannel.TELEGRAM, 1, 0),
        (NotificationChannel.EMAIL, 0, 1),
        (NotificationChannel.BOTH, 1, 1),
        (NotificationChannel.NONE, 0, 0),
    ],
)
def test_a_notification_is_queued_only_on_the_chosen_channel(
    channels: Channels, channel: NotificationChannel, chat: int, email: int
) -> None:
    channels.choose(NotificationEvent.CYCLE_FAILED, channel)

    channels.notify(FAILED_ALFA)

    assert len(channels.chat_texts()) == chat
    assert len(channels.email_texts()) == email


def test_the_exception_of_the_flow_of_the_event_wins_over_the_general_choice(channels: Channels) -> None:
    channels.choose(NotificationEvent.CYCLE_FAILED, NotificationChannel.NONE)
    channels.except_flow(ALFA, NotificationEvent.CYCLE_FAILED, NotificationChannel.TELEGRAM)

    channels.notify(FAILED_ALFA)
    channels.notify(FAILED_BETA)

    assert channels.chat_texts() == [FAILED_ALFA.text]


def test_an_event_of_a_flow_no_more_listed_follows_the_general_choice(channels: Channels) -> None:
    channels.except_flow(ALFA, NotificationEvent.CYCLE_FAILED, NotificationChannel.NONE)
    channels.flows.flows = (BETA,)

    channels.notify(FAILED_ALFA)

    assert channels.chat_texts() == [FAILED_ALFA.text]


def test_an_event_of_the_account_follows_the_general_choice(channels: Channels) -> None:
    channels.choose(NotificationEvent.RECONCILIATION_ALARM, NotificationChannel.EMAIL)

    channels.notify(ALARM)

    assert channels.chat_texts() == []
    assert channels.email_texts() == [ALARM.text]


def test_the_risk_decisions_are_silent_until_the_user_chooses(channels: Channels) -> None:
    channels.notify(Notification.opening_blocked("alfa", "BTC", "confidenza 40 sotto la minima 60"))

    assert channels.chat_texts() == []
    assert channels.email_texts() == []


def test_the_test_notification_is_no_event_and_reaches_every_linked_channel(channels: Channels) -> None:
    for event in NotificationEvent:
        channels.choose(event, NotificationChannel.NONE)

    channels.notify(Notification.test())

    assert channels.chat_texts() == [Notification.test().text]
    assert channels.email_texts() == [Notification.test().text]


def test_a_chosen_channel_not_linked_sends_nothing_on_it(channels: Channels) -> None:
    channels.chats.clear()
    channels.choose(NotificationEvent.CYCLE_FAILED, NotificationChannel.BOTH)

    channels.notify(FAILED_ALFA)

    assert channels.messenger.sent == []
    assert channels.email_texts() == [FAILED_ALFA.text]


def test_the_choices_of_another_tenant_never_change_the_channels_of_a_tenant(channels: Channels) -> None:
    channels.choose(NotificationEvent.CYCLE_FAILED, NotificationChannel.NONE, BRUNO)

    channels.notify(FAILED_ALFA)

    assert channels.chat_texts() == [FAILED_ALFA.text]
