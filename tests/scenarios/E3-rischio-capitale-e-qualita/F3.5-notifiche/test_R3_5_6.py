"""R3.5.6: every notification leads to the page of the dashboard it is about, on the notification use cases with the
fake adapters (ADR destinazioni-delle-notifiche-nella-dashboard, ADR link-nei-messaggi-telegram-ed-email).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.notify_cycle_failed import NotifyCycleFailedUseCase
from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.notifications.notify_position_opened import NotifyPositionOpenedUseCase
from autotrading.application.notifications.notify_unattributable_movement import (
    NotifyUnattributableMovementUseCase,
)
from autotrading.application.notifications.ports import NotificationRoutes
from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.notifications.notification_link import NotificationLink
from autotrading.domain.notifications.notification_target import NotificationTarget, TargetKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_status import FakeFlowStatusAdapter
from tests.fakes.linked_chat_repository import InMemoryLinkedChatRepositoryAdapter, LinkedChatStore
from tests.fakes.mailer import FakeMailerAdapter
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.notification_email_repository import (
    InMemoryNotificationEmailRepositoryAdapter,
    NotificationEmailStore,
)
from tests.fakes.notification_link import FakeNotificationLinkAdapter
from tests.fakes.outbox import InMemoryOutboxAdapter
from tests.support.mail_servers import MailServers
from tests.support.notifications import chat_named, notification_routes
from tests.support.steps import quoted

scenarios("E3-rischio-capitale-e-qualita/F3.5-notifiche/R3.5.6-link-alla-dashboard-nelle-notifiche.feature")

CURRENCY = "USDC"
USER = "anna"
ADDRESS = "anna@example.com"
ASSET = "BTC"
CLOSED_AT = datetime(2026, 11, 17, 10, 15, tzinfo=UTC)
TAB_OF = {"Posizioni": TargetKind.OPEN_POSITION, "Posizioni chiuse": TargetKind.CLOSED_POSITION}
CLOSING_OF = {
    "chiusura di una posizione": ("4,20", "decisione dell'agente"),
    "stop loss attivato": ("-5,10", "stop loss"),
    "take profit attivato": ("4,90", "take profit"),
    "liquidazione di una posizione": ("-48,00", "liquidazione"),
}


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


class Notices:
    """The channels of anna, reached on Telegram and by email, and the notifications her flows and account send."""

    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.chats: LinkedChatStore = {self.tenant_id: LinkedChat(self.tenant_id, chat_named(USER))}
        self.emails: NotificationEmailStore = {
            self.tenant_id: NotificationEmail(self.tenant_id, EmailAddress.parse(ADDRESS))
        }
        self.messenger = FakeMessengerAdapter()
        self.mailer = FakeMailerAdapter()
        self.mail_servers = MailServers()
        self.mail_servers.configure(self.tenant_id, ADDRESS)
        self.links = FakeNotificationLinkAdapter()
        self.outbox = InMemoryOutboxAdapter()
        self.outbox.process(
            DeliverOutboxMessageUseCase(self.messenger, self.mailer, self.mail_servers.access_of).execute
        )
        self.flow_ids: dict[str, UUID] = {}
        self.account_id = uuid4()
        self.pending: Callable[[], None] = lambda: None

    @property
    def notify(self) -> NotifyUseCase:
        chats = InMemoryLinkedChatRepositoryAdapter(self.chats, self.tenant_id)
        emails = InMemoryNotificationEmailRepositoryAdapter(self.emails, self.tenant_id)
        servers = self.mail_servers.repository(self.tenant_id)
        return NotifyUseCase(chats, emails, servers, self.outbox, self.routes)

    @property
    def routes(self) -> NotificationRoutes:
        # The scenarios read the notification on both channels: the tenant chose both for every event (R3.5.3).
        preferences = ChannelPreferences.of(self.tenant_id)
        for event in NotificationEvent:
            preferences = preferences.choosing(event, frozenset(NotificationChannel))
        return notification_routes(self.tenant_id, {self.tenant_id: preferences}, self.links)

    @property
    def notify_flow(self) -> NotifyFlowEventUseCase:
        return NotifyFlowEventUseCase(self.notify, FakeFlowStatusAdapter())

    def flow_id(self, flow: str) -> UUID:
        return self.flow_ids.setdefault(flow, uuid4())

    def open_position(self, flow: str) -> None:
        use_case = NotifyPositionOpenedUseCase(self.notify_flow, CURRENCY)
        use_case.execute(self.flow_id(flow), flow, ASSET, "long", 3, Decimal(150))

    def close_position(self, flow: str, pnl: str, reason: str) -> None:
        use_case = NotifyPositionClosedUseCase(self.notify_flow, CURRENCY)
        use_case.execute(self.flow_id(flow), flow, ASSET, amount(pnl), reason, CLOSED_AT)

    def last_links(self) -> list[NotificationLink]:
        [*_, last] = self.messenger.links_received_by(chat_named(USER))
        return list(last)

    def link_to(self, target: NotificationTarget) -> NotificationLink:
        return NotificationLink(target.label, self.links.address_of(target))


@pytest.fixture
def notices() -> Notices:
    return Notices()


# Given


@given(quoted('un flusso "{flow}" con un ciclo fallito'))
def flow_with_failed_cycle(notices: Notices, flow: str) -> None:
    notices.pending = lambda: NotifyCycleFailedUseCase(notices.notify_flow).execute(
        notices.flow_id(flow), flow, "timeout"
    )


@given(quoted('un flusso "{flow}" con l\'evento "{event}" su una posizione'))
def flow_with_position_event(notices: Notices, flow: str, event: str) -> None:
    if event == "apertura di una posizione":
        notices.pending = lambda: notices.open_position(flow)
        return
    pnl, reason = CLOSING_OF[event]
    notices.pending = lambda: notices.close_position(flow, pnl, reason)


@given(quoted('un movimento non attribuibile sul conto "{account}"'))
def unattributable_movement(notices: Notices, account: str) -> None:
    use_case = NotifyUnattributableMovementUseCase(notices.notify, CURRENCY)
    notices.pending = lambda: use_case.execute(notices.account_id, account, Decimal(25))


@given("una notifica con i link al flusso e all'operazione")
def notification_with_both_links(notices: Notices) -> None:
    notices.pending = lambda: notices.open_position("prova-btc")


# When


@when("ricevo la notifica del ciclo fallito")
@when("ricevo la notifica")
@when("arriva su Telegram")
def notification_arrives(notices: Notices) -> None:
    notices.pending()


@when("arriva per email")
def email_arrives(notices: Notices) -> None:
    assert notices.mailer.received_by(ADDRESS), "the notification left only on Telegram"


# Then


@then(quoted('la notifica porta alla pagina del flusso "{flow}"'))
def leads_to_flow(notices: Notices, flow: str) -> None:
    assert notices.last_links() == [notices.link_to(NotificationTarget.flow(notices.flow_id(flow)))]


@then(quoted('la notifica porta alla scheda "{tab}" del flusso con quella posizione evidenziata'))
def leads_to_position(notices: Notices, tab: str) -> None:
    flow_id = notices.flow_id("prova-btc")
    position = (
        NotificationTarget.open_position(flow_id, ASSET)
        if TAB_OF[tab] is TargetKind.OPEN_POSITION
        else NotificationTarget.closed_position(flow_id, ASSET, CLOSED_AT)
    )
    assert notices.link_to(position) in notices.last_links(), notices.last_links()


@then("porta anche alla pagina del flusso")
def leads_to_flow_too(notices: Notices) -> None:
    flow = notices.link_to(NotificationTarget.flow(notices.flow_id("prova-btc")))
    assert notices.last_links()[0] == flow, notices.last_links()


@then("la notifica porta alla pagina Allarmi del conto")
def leads_to_alarms(notices: Notices) -> None:
    assert notices.last_links() == [notices.link_to(NotificationTarget.account_alarms(notices.account_id))]


@then(quoted('sotto il messaggio ci sono i pulsanti "{first}" e "{second}"'))
def buttons_under_message(notices: Notices, first: str, second: str) -> None:
    assert [link.label for link in notices.last_links()] == [first, second]


@then("i link sono in fondo al testo")
def links_at_the_bottom(notices: Notices) -> None:
    [email] = notices.mailer.received_by(ADDRESS)
    lines = email.text.splitlines()
    links = notices.last_links()
    assert lines[-len(links) - 1] == ""
    assert lines[-len(links) :] == [f"{link.label}: {link.url}" for link in links]
