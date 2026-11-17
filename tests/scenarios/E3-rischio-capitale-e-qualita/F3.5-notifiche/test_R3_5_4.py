"""R3.5.4: notifications told by an icon, a title and their values one per line, closed by the state of the flow, on
the notification use cases with the fake adapters (ADR notifica-strutturata-con-icona-titolo-e-valori, ADR
stato-del-flusso-in-ogni-notifica, ADR resa-della-notifica-per-telegram-ed-email).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.notify_cycle_failed import NotifyCycleFailedUseCase
from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.application.notifications.notify_flow_paused import NotifyFlowPausedUseCase
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.notifications.notify_position_opened import NotifyPositionOpenedUseCase
from autotrading.application.notifications.ports import NotificationRoutes
from autotrading.application.notifications.send_linked_chat_test_notification import (
    SendLinkedChatTestNotificationUseCase,
)
from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.flow_status import FlowStatusFigures, NotifiedFlowStatus, RecordedEquity
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_status import FakeFlowStatusAdapter
from tests.fakes.linked_chat_repository import InMemoryLinkedChatRepositoryAdapter, LinkedChatStore
from tests.fakes.mailer import FakeMailerAdapter, SentEmail
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.notification_email_repository import (
    InMemoryNotificationEmailRepositoryAdapter,
    NotificationEmailStore,
)
from tests.fakes.outbox import InMemoryOutboxAdapter
from tests.support.mail_servers import MailServers
from tests.support.notifications import chat_named, notification_routes
from tests.support.steps import quoted

scenarios(
    "E3-rischio-capitale-e-qualita/F3.5-notifiche/R3.5.4-notifiche-leggibili-con-icone-e-stato-del-flusso.feature"
)

CURRENCY = "USDC"
ADDRESS = "anna@example.com"
CLOSED_AT = datetime(2026, 11, 17, 10, 15, tzinfo=UTC)
STATUS_OF = {"attivo": NotifiedFlowStatus.ACTIVE, "in pausa": NotifiedFlowStatus.PAUSED}


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


class Notices:
    """The channels of anna, the state of her flows and the notification use cases that tell what happens to them."""

    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.chats: LinkedChatStore = {}
        self.emails: NotificationEmailStore = {}
        self.messenger = FakeMessengerAdapter()
        self.mailer = FakeMailerAdapter()
        self.mail_servers = MailServers()
        self.flow_status = FakeFlowStatusAdapter()
        self.outbox = InMemoryOutboxAdapter()
        self.outbox.process(
            DeliverOutboxMessageUseCase(self.messenger, self.mailer, self.mail_servers.access_of).execute
        )
        self.user = ""
        self.flow_ids: dict[str, UUID] = {}

    @property
    def linked_chats(self) -> InMemoryLinkedChatRepositoryAdapter:
        return InMemoryLinkedChatRepositoryAdapter(self.chats, self.tenant_id)

    @property
    def notify(self) -> NotifyUseCase:
        emails = InMemoryNotificationEmailRepositoryAdapter(self.emails, self.tenant_id)
        servers = self.mail_servers.repository(self.tenant_id)
        return NotifyUseCase(self.linked_chats, emails, servers, self.outbox, self.every_channel)

    @property
    def every_channel(self) -> NotificationRoutes:
        # The scenarios read the notification on both channels: the tenant chose both for every event (R3.5.3).
        preferences = ChannelPreferences.of(self.tenant_id)
        for event in NotificationEvent:
            preferences = preferences.choosing(event, frozenset(NotificationChannel))
        return notification_routes(self.tenant_id, {self.tenant_id: preferences})

    @property
    def notify_flow(self) -> NotifyFlowEventUseCase:
        return NotifyFlowEventUseCase(self.notify, self.flow_status)

    def flow_id(self, flow: str) -> UUID:
        return self.flow_ids.setdefault(flow, uuid4())

    def open_position(self, flow: str, direction: str = "long", asset: str = "BTC") -> None:
        use_case = NotifyPositionOpenedUseCase(self.notify_flow, CURRENCY)
        use_case.execute(self.flow_id(flow), flow, asset, direction, 3, Decimal(150))

    def close_position(self, flow: str, pnl: str, reason: str) -> None:
        use_case = NotifyPositionClosedUseCase(self.notify_flow, CURRENCY)
        use_case.execute(self.flow_id(flow), flow, "BTC", amount(pnl), reason, CLOSED_AT)

    def received(self) -> list[str]:
        return self.messenger.received_by(chat_named(self.user))

    def last_message(self) -> list[str]:
        [*_, last] = self.received()
        return last.splitlines()


EVENTS: dict[str, Callable[[Notices, str], None]] = {
    "chiusura in profitto": lambda notices, flow: notices.close_position(flow, "4,20", "decisione dell'agente"),
    "chiusura in perdita": lambda notices, flow: notices.close_position(flow, "-3,10", "decisione dell'agente"),
    "chiusura per stop loss": lambda notices, flow: notices.close_position(flow, "-5,10", "stop loss"),
    "chiusura per take profit": lambda notices, flow: notices.close_position(flow, "4,90", "take profit"),
    "ciclo fallito": lambda notices, flow: NotifyCycleFailedUseCase(notices.notify_flow).execute(
        notices.flow_id(flow), flow, "timeout"
    ),
    "pausa per errore permanente": lambda notices, flow: NotifyFlowPausedUseCase(notices.notify_flow).execute(
        notices.flow_id(flow), flow, "credito esaurito presso openrouter"
    ),
}


@pytest.fixture
def notices() -> Notices:
    return Notices()


# Given


@given(quoted('che "{user}" ha la chat Telegram collegata'))
def chat_linked(notices: Notices, user: str) -> None:
    notices.user = user
    notices.chats[notices.tenant_id] = LinkedChat(notices.tenant_id, chat_named(user))


@given(
    parsers.re(
        r'^che il flusso "(?P<flow>[^"]+)" vale (?P<value>[\d,]+) USDC, ha PnL dall\'avvio \+(?P<pnl>[\d,]+) USDC, '
        r"(?P<positions>\d+) posizioni aperte ed è (?P<status>attivo|in pausa)$"
    )
)
def flow_state(notices: Notices, *, flow: str, value: str, pnl: str, positions: str, status: str) -> None:
    equity = amount(value)
    recorded = RecordedEquity(equity, equity - amount(pnl), Decimal(0))
    notices.flow_status.figures[flow] = FlowStatusFigures(STATUS_OF[status], int(positions), CURRENCY, recorded)


@given(quoted('che "{user}" riceve le notifiche anche per email'))
def email_too(notices: Notices, user: str) -> None:
    assert user == notices.user
    notices.mail_servers.configure(notices.tenant_id, ADDRESS)
    notices.emails[notices.tenant_id] = NotificationEmail(notices.tenant_id, EmailAddress.parse(ADDRESS))


# When


@when(quoted('"{flow}" apre una posizione {direction} su {asset}'))
def opens_on(notices: Notices, flow: str, direction: str, asset: str) -> None:
    notices.open_position(flow, direction, asset)


@when(quoted('"{flow}" apre una posizione'))
def opens(notices: Notices, flow: str) -> None:
    notices.open_position(flow)


@when(quoted('accade {event} nel flusso "{flow}"'))
def event_happens(notices: Notices, event: str, flow: str) -> None:
    EVENTS[event](notices, flow)


@when(quoted('"{user}" chiede la notifica di prova'))
def trial_asked(notices: Notices, user: str) -> None:
    assert user == notices.user
    SendLinkedChatTestNotificationUseCase(notices.linked_chats, notices.notify).execute()


# Then


@then(quoted('"{user}" riceve una notifica che inizia con "{title}"'))
def receives_starting_with(notices: Notices, user: str, title: str) -> None:
    assert user == notices.user
    assert notices.last_message()[0].startswith(title), notices.received()


@then("i valori della posizione uno per riga")
def values_one_per_line(notices: Notices) -> None:
    lines = notices.last_message()
    assert lines[1] == ""
    assert lines[2:6] == ["Asset: BTC", "Direzione: long", "Leva: 3", "Valore: 150 USDC"]


@then(quoted('in fondo "{status}"'))
def status_at_the_bottom(notices: Notices, status: str) -> None:
    assert notices.last_message()[-1] == status


@then(quoted('la notifica inizia con "{icon}"'))
def starts_with_icon(notices: Notices, icon: str) -> None:
    assert notices.last_message()[0].startswith(f"{icon} alfa: "), notices.received()


@then(quoted('l\'email ha oggetto "{subject}" e lo stesso contenuto del messaggio Telegram'))
def same_email(notices: Notices, subject: str) -> None:
    [message] = notices.received()
    [email] = notices.mailer.received_by(ADDRESS)
    assert email == SentEmail(EmailAddress.parse(ADDRESS), subject, message)


@then("la notifica ha icona e titolo e non ha lo stato del flusso")
def icon_and_title_without_status(notices: Notices) -> None:
    title, *body = notices.last_message()
    icon, heading = title.split(" ", 1)
    assert icon
    assert not icon.isalnum()
    assert heading == "AutoTrading: prova delle notifiche"
    assert not any(line.startswith("Flusso:") for line in body), body
    assert notices.flow_status.asked == []
