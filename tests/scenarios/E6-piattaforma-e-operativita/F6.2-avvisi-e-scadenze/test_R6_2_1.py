"""R6.2.1: every notification the worker generates is kept for the bell of the tenant, read, counted and marked read
through the use cases of the API, on the fake adapters (ADR notifiche-nell-app-salvate-per-tenant). playwright-bdd runs
the same scenarios on the bell of the dashboard (ADR campanello-delle-notifiche-nella-dashboard).
"""

from dataclasses import dataclass, field
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.notifications.list_inbox_notifications import ListInboxNotificationsCommand
from autotrading.application.notifications.mark_notification_read import MarkNotificationReadCommand
from autotrading.domain.notifications.inbox_notification import InboxNotification
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Notification, NotificationLine
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.notifications.notification_target import TargetKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.notifications import chat_named
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E6-piattaforma-e-operativita/F6.2-avvisi-e-scadenze/R6.2.1-campanello-delle-notifiche.feature")

# «Flusso alfa in pausa», as a notification tells it: the flow, then what happened to it.
PAUSED_FLOW = "alfa"
PAUSED_HEADING = f"{PAUSED_FLOW}: in pausa"


@dataclass
class Bell:
    """The platform of the scenario, with what anna sees in her bell."""

    platform: Platform = field(default_factory=Platform)
    flows: dict[str, UUID] = field(default_factory=dict)
    shown: int | None = None
    listed: list[InboxNotification] = field(default_factory=list)
    opened: InboxNotification | None = None
    told: str = ""

    def tenant(self, user: str = "anna") -> TenantId:
        return self.platform.tenant_of(user)

    def use_cases(self, user: str = "anna") -> TenantUseCases:
        return self.platform.use_cases_of(user)

    def notify(self, notification: Notification, user: str = "anna") -> None:
        """What the worker does with every notification of the tenant, whatever its channels (R6.2.1)."""
        self.platform.notify_for(self.tenant(user)).execute(notification)
        self.platform.worker_clock.current += timedelta(minutes=1)

    def notify_cycle_failed(self, flow: str, user: str = "anna") -> None:
        self.notify(Notification.cycle_failed(self.flow_id(flow), flow, "exchange non raggiungibile"), user)

    def flow_id(self, flow: str) -> UUID:
        return self.flows.setdefault(flow, uuid4())

    def all_notifications(self, user: str = "anna") -> list[InboxNotification]:
        page = self.use_cases(user).list_inbox_notifications.execute(ListInboxNotificationsCommand())
        return list(page.notifications)

    def unread_count(self) -> int:
        return self.use_cases().count_unread_notifications.execute()


@pytest.fixture
def bell() -> Bell:
    return Bell()


# Given


@given(quoted('che "{user}" è nella dashboard'))
def in_dashboard(bell: Bell, user: str) -> None:
    assert bell.tenant(user) == bell.platform.tenant_of(user)


@given(quoted('che "{user}" ha {count} notifiche non lette'))
def unread_notifications(bell: Bell, user: str, count: str) -> None:
    for index in range(int(count)):
        bell.notify_cycle_failed(f"flusso-{index}", user)
    assert [notification.is_read for notification in bell.all_notifications(user)] == [False] * int(count)


@given(quoted('che "{user}" ha la notifica "{title}"'))
def the_notification(bell: Bell, user: str, title: str) -> None:
    assert title == f"Flusso {PAUSED_FLOW} in pausa"
    paused = Notification.of_flow(
        NotificationEvent.FLOW_PAUSED,
        bell.flow_id(PAUSED_FLOW),
        PAUSED_FLOW,
        "in pausa",
        NotificationLine("Motivo", "credito esaurito"),
    )
    bell.notify(paused, user)


@given(quoted('che "{user}" non ha collegato Telegram'))
def telegram_not_linked(bell: Bell, user: str) -> None:
    assert bell.tenant(user) not in bell.platform.chats


@given(quoted('che "{user}" ha una notifica'))
def other_user_notification(bell: Bell, user: str) -> None:
    bell.notify_cycle_failed("beta", user)
    [theirs] = bell.all_notifications(user)
    bell.told = theirs.title


@given(quoted('che "{user}" ha collegato Telegram'))
def telegram_linked(bell: Bell, user: str) -> None:
    tenant_id = bell.tenant(user)
    bell.platform.chats[tenant_id] = LinkedChat(tenant_id, chat_named(user))


@given("che Telegram non risponde")
def telegram_unreachable(bell: Bell) -> None:
    bell.platform.messenger.reachable = False


@given(
    quoted(
        'che "{user}" ha ricevuto la notifica "{old}" {old_days} giorni fa '
        'e la notifica "{recent}" {recent_days} giorni fa'
    )
)
def aged_notifications(  # noqa: PLR0917 - one argument per value of the step
    bell: Bell, user: str, old: str, old_days: str, recent: str, recent_days: str
) -> None:
    now = bell.platform.worker_clock.current
    for flow, days in ((old, old_days), (recent, recent_days)):
        bell.platform.worker_clock.current = now - timedelta(days=int(days))
        bell.notify_cycle_failed(flow, user)
    bell.platform.worker_clock.current = now


# When


@when(quoted('"{user}" guarda il campanello accanto al suo nome'))
def looks_at_bell(bell: Bell, user: str) -> None:
    assert user == "anna"
    bell.shown = bell.unread_count()


@when(quoted('"{user}" apre il campanello e sceglie la notifica'))
def opens_and_chooses(bell: Bell, user: str) -> None:
    [chosen] = bell.all_notifications(user)
    bell.use_cases(user).mark_notification_read.execute(MarkNotificationReadCommand(chosen.id))
    bell.opened = chosen


@when(quoted('la piattaforma genera una notifica per "{user}"'))
def platform_notifies(bell: Bell, user: str) -> None:
    bell.notify_cycle_failed("gamma", user)
    bell.told = "gamma: ciclo fallito"


@when(quoted('"{user}" le segna tutte come lette'))
def marks_all_read(bell: Bell, user: str) -> None:
    bell.use_cases(user).mark_all_notifications_read.execute()


@when(quoted('"{user}" apre il campanello'))
def opens_bell(bell: Bell, user: str) -> None:
    bell.listed = bell.all_notifications(user)


# Then


@then(quoted("il campanello mostra {count}"))
def bell_shows(bell: Bell, count: str) -> None:
    assert bell.shown == int(count)


@then(quoted('la dashboard apre la pagina del flusso "{flow}" e la notifica è letta'))
def opens_flow_page_and_reads(bell: Bell, flow: str) -> None:
    assert bell.opened is not None
    first = bell.opened.targets[0]
    assert (bell.opened.title, first.kind, first.owner_id) == (PAUSED_HEADING, TargetKind.FLOW, bell.flow_id(flow))
    [read] = bell.all_notifications()
    assert (read.id, read.is_read) == (bell.opened.id, True)


@then("la notifica compare nel campanello")
def notification_in_bell(bell: Bell) -> None:
    # No chat, no message: the bell has it all the same, not because nothing was generated.
    assert bell.platform.outbox.messages == []
    assert [notification.title for notification in bell.all_notifications()] == [bell.told]
    assert bell.unread_count() == 1


@then("la notifica compare nel campanello senza il messaggio Telegram")
def notification_in_bell_without_message(bell: Bell) -> None:
    assert bell.platform.messenger.sent == []
    assert [notification.title for notification in bell.all_notifications()] == [bell.told]
    assert bell.unread_count() == 1


@then(quoted('il campanello contiene la notifica "{recent}" e la nuova, non la notifica "{old}"'))
def kept_for_retention(bell: Bell, recent: str, old: str) -> None:
    titles = [notification.title for notification in bell.all_notifications()]
    assert titles == [bell.told, f"{recent}: ciclo fallito"]
    assert f"{old}: ciclo fallito" not in titles


@then("il campanello non mostra alcun numero")
def bell_shows_nothing(bell: Bell) -> None:
    assert bell.unread_count() == 0
    # The three notifications are still there, read: none was forgotten to empty the bell.
    assert [notification.is_read for notification in bell.all_notifications()] == [True, True, True]


@then(quoted('la notifica di "{user}" non compare'))
def other_notification_absent(bell: Bell, user: str) -> None:
    assert [notification.title for notification in bell.all_notifications(user)] == [bell.told]
    assert bell.told not in [notification.title for notification in bell.listed]
