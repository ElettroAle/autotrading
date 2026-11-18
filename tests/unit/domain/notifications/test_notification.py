"""ADR notifica-strutturata-con-icona-titolo-e-valori: icon, title with the flow or account and the event, values one
per line (R1.8.2, R3.5.1, R3.5.4).
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.errors import InvalidNotificationError
from autotrading.domain.notifications.flow_status import FlowStatusLine
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Amount, Notification, NotificationLine
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.notifications.notification_target import NotificationTarget
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

OPENED = "\U0001f7e2"
PROFIT = "✅"
LOSS = "\U0001f53b"
STOP_LOSS = "\U0001f6d1"
TAKE_PROFIT = "\U0001f3af"
WARNING = "⚠️"
PAUSE = "⏸️"
ALARM = "\U0001f6a8"
FLOW_ID = uuid4()
ALERT_ID = uuid4()
CLOSED_AT = datetime(2026, 11, 17, 10, 15, tzinfo=UTC)
STATUS = FlowStatusLine("Flusso: 312,40 USDC · PnL +12,40 USDC · 2 posizioni aperte · attivo")


def usdc(value: str | int) -> Amount:
    return Amount(Decimal(value), "USDC")


@pytest.mark.parametrize(
    ("notification", "title", "lines"),
    [
        (
            Notification.position_opened(FLOW_ID, "alfa", "BTC", "long", 3, usdc(150)),
            f"{OPENED} alfa: posizione aperta",
            ("Asset: BTC", "Direzione: long", "Leva: 3", "Valore: 150 USDC"),
        ),
        (
            Notification.position_closed(FLOW_ID, "alfa", "BTC", usdc("4.20"), "decisione dell'agente", CLOSED_AT),
            f"{PROFIT} alfa: posizione chiusa",
            ("Asset: BTC", "PnL: 4,20 USDC"),
        ),
        (
            Notification.position_closed(FLOW_ID, "alfa", "ETH", usdc("-0.5"), "comando manuale", CLOSED_AT),
            f"{LOSS} alfa: posizione chiusa",
            ("Asset: ETH", "PnL: -0,50 USDC"),
        ),
        (
            Notification.position_closed(FLOW_ID, "alfa", "BTC", usdc("-5.1"), "stop loss", CLOSED_AT),
            f"{STOP_LOSS} alfa: chiusa per stop loss",
            ("Asset: BTC", "PnL: -5,10 USDC"),
        ),
        (
            Notification.position_closed(FLOW_ID, "alfa", "BTC", usdc("4.9"), "take profit", CLOSED_AT),
            f"{TAKE_PROFIT} alfa: chiusa per take profit",
            ("Asset: BTC", "PnL: 4,90 USDC"),
        ),
        (
            Notification.position_closed(FLOW_ID, "alfa", "BTC", usdc("-48.5"), "liquidazione", CLOSED_AT),
            f"{LOSS} alfa: posizione liquidata",
            ("Asset: BTC", "PnL: -48,50 USDC"),
        ),
        (
            Notification.position_liquidated(FLOW_ID, "alfa", "BTC", usdc(-48), CLOSED_AT),
            f"{LOSS} alfa: posizione liquidata",
            ("Asset: BTC", "PnL: -48 USDC"),
        ),
        (
            Notification.opening_reduced(FLOW_ID, "alfa", "BTC", usdc(150), usdc(100)),
            f"{WARNING} alfa: apertura ridotta",
            ("Asset: BTC", "Margine richiesto: 150 USDC", "Margine approvato: 100 USDC"),
        ),
        (
            Notification.opening_blocked(FLOW_ID, "alfa", "BTC", "confidenza 40 sotto la minima 60"),
            f"{WARNING} alfa: apertura non eseguita",
            ("Asset: BTC", "Motivo: confidenza 40 sotto la minima 60"),
        ),
        (
            Notification.cash_out_done(FLOW_ID, "alfa", usdc(118)),
            f"{PROFIT} alfa: incasso eseguito",
            ("Importo: 118 USDC",),
        ),
        (
            Notification.emergency_closing_done(1, ("alfa",)),
            f"{ALARM} chiusura di emergenza: eseguita",
            ("Posizioni chiuse: 1", "Flussi in pausa: alfa"),
        ),
        (
            Notification.emergency_closing_done(3, ("alfa", "beta")),
            f"{ALARM} chiusura di emergenza: eseguita",
            ("Posizioni chiuse: 3", "Flussi in pausa: alfa, beta"),
        ),
        (
            Notification.emergency_closing_done(0, ()),
            f"{ALARM} chiusura di emergenza: eseguita",
            ("Posizioni chiuse: 0", "Flussi in pausa: nessuno"),
        ),
        (Notification.cycle_failed(FLOW_ID, "alfa", "timeout"), f"{WARNING} alfa: ciclo fallito", ("Errore: timeout",)),
        (
            Notification.order_rejected(FLOW_ID, "alfa", "Order rejected"),
            f"{WARNING} alfa: ordine rifiutato",
            ("Errore: Order rejected",),
        ),
        (
            Notification.flow_paused(FLOW_ID, "alfa", "credito esaurito presso openrouter", ALERT_ID),
            f"{PAUSE} alfa: in pausa",
            ("Motivo: credito esaurito presso openrouter",),
        ),
        (
            Notification.openings_suspended(FLOW_ID, "alfa", "perdita giornaliera 6% oltre il 5%"),
            f"{PAUSE} alfa: aperture sospese",
            ("Motivo: perdita giornaliera 6% oltre il 5%",),
        ),
        (
            Notification.unattributable_position(ALERT_ID, "conto-1", "SOL"),
            f"{ALARM} conto-1: posizione non attribuibile",
            ("Asset: SOL",),
        ),
        (
            Notification.unattributable_fill(ALERT_ID, "conto-1", "ETH"),
            f"{ALARM} conto-1: esecuzione non attribuibile",
            ("Asset: ETH",),
        ),
        (
            Notification.reconciliation_alarm(ALERT_ID, "test-1", usdc(980), usdc(1000)),
            f"{ALARM} test-1: allarme di riconciliazione",
            ("Saldo letto: 980 USDC", "Saldo atteso: 1000 USDC"),
        ),
    ],
)
def test_each_event_has_its_icon_its_title_and_its_values_one_per_line(
    notification: Notification, title: str, lines: tuple[str, ...]
) -> None:
    assert notification.title == title
    assert notification.body_lines() == lines


def test_the_text_is_the_title_a_blank_line_and_the_values() -> None:
    notification = Notification.cycle_failed(FLOW_ID, "alfa", "timeout")

    assert notification.text == f"{WARNING} alfa: ciclo fallito\n\nErrore: timeout"


def test_the_state_of_the_flow_closes_the_text() -> None:
    notification = Notification.position_opened(FLOW_ID, "alfa", "BTC", "long", 3, usdc(150)).with_flow_status(STATUS)

    assert notification.text.splitlines() == [
        f"{OPENED} alfa: posizione aperta",
        "",
        "Asset: BTC",
        "Direzione: long",
        "Leva: 3",
        "Valore: 150 USDC",
        "Flusso: 312,40 USDC · PnL +12,40 USDC · 2 posizioni aperte · attivo",
    ]
    assert notification.body_lines()[-1] == STATUS.text


def test_a_notification_without_values_is_its_title() -> None:
    notification = Notification("alfa", "in pausa", (), NotificationEvent.FLOW_PAUSED, PAUSE)

    assert notification.text == f"{PAUSE} alfa: in pausa"


def test_a_closing_at_zero_is_no_profit() -> None:
    assert Notification.position_closed(FLOW_ID, "alfa", "BTC", usdc(0), "stop del flusso", CLOSED_AT).icon == LOSS


def test_a_line_reads_label_and_value() -> None:
    assert str(NotificationLine("Leva", "3")) == "Leva: 3"


def test_an_amount_never_turns_into_an_exponent() -> None:
    assert str(Amount(Decimal("1E+2"), "USDC")) == "100 USDC"


@pytest.mark.parametrize("subject", ["", "  "])
def test_a_notification_without_its_subject_is_a_defect(subject: str) -> None:
    with pytest.raises(InvalidNotificationError, match=r"^notifica senza flusso o conto$"):
        Notification.cycle_failed(FLOW_ID, subject, "timeout")


def test_a_linked_chat_belongs_to_its_tenant() -> None:
    tenant = TenantId.new()
    chat = LinkedChat(tenant, ChatId(-100123))

    assert (chat.tenant_id, chat.chat_id.value) == (tenant, -100123)
    assert isinstance(chat, TenantOwned)


def test_the_test_notification_has_icon_and_title_and_says_where_the_notifications_arrive() -> None:
    assert Notification.test().text == (
        "\U0001f514 AutoTrading: prova delle notifiche\n\nEsito: le notifiche dei tuoi flussi arrivano qui"
    )


def test_an_opening_is_told_by_its_value_in_whole_units() -> None:
    notification = Notification.position_opened(FLOW_ID, "alfa", "BTC", "long", 3, usdc("20.006"))

    assert notification.body_lines()[-1] == "Valore: 20 USDC"


@pytest.mark.parametrize(
    ("notification", "subject"),
    [
        (Notification.flow_paused(FLOW_ID, "alfa", "credito esaurito", ALERT_ID), f"{PAUSE} alfa: in pausa"),
        (Notification.cycle_failed(FLOW_ID, "alfa", "timeout, riprova"), f"{WARNING} alfa: ciclo fallito"),
        (
            Notification.unattributable_position(ALERT_ID, "conto-1", "SOL"),
            f"{ALARM} conto-1: posizione non attribuibile",
        ),
        (Notification.test(), "\U0001f514 AutoTrading: prova delle notifiche"),
    ],
)
def test_the_subject_of_an_email_is_the_title(notification: Notification, subject: str) -> None:
    assert notification.title == subject


@pytest.mark.parametrize(
    ("notification", "event"),
    [
        (Notification.position_opened(FLOW_ID, "alfa", "BTC", "long", 3, usdc(150)), "POSITION_OPENED"),
        (
            Notification.position_closed(FLOW_ID, "alfa", "BTC", usdc(1), "stop del flusso", CLOSED_AT),
            "POSITION_CLOSED",
        ),
        (Notification.position_closed(FLOW_ID, "alfa", "BTC", usdc(1), "stop loss", CLOSED_AT), "STOP_LOSS"),
        (Notification.position_closed(FLOW_ID, "alfa", "BTC", usdc(1), "take profit", CLOSED_AT), "TAKE_PROFIT"),
        (Notification.position_closed(FLOW_ID, "alfa", "BTC", usdc(1), "liquidazione", CLOSED_AT), "LIQUIDATION"),
        (Notification.position_liquidated(FLOW_ID, "alfa", "BTC", usdc(1), CLOSED_AT), "LIQUIDATION"),
        (Notification.cycle_failed(FLOW_ID, "alfa", "timeout"), "CYCLE_FAILED"),
        (Notification.order_rejected(FLOW_ID, "alfa", "rifiutato"), "ORDER_REJECTED"),
        (Notification.flow_paused(FLOW_ID, "alfa", "credito esaurito", ALERT_ID), "FLOW_PAUSED"),
        (Notification.openings_suspended(FLOW_ID, "alfa", "perdita giornaliera 6% oltre il 5%"), "MAXIMUM_LOSS"),
        (Notification.opening_reduced(FLOW_ID, "alfa", "BTC", usdc(2), usdc(1)), "OPENING_REDUCED"),
        (Notification.opening_blocked(FLOW_ID, "alfa", "BTC", "motivo"), "OPENING_BLOCKED"),
        (Notification.unattributable_position(ALERT_ID, "conto-1", "SOL"), "UNATTRIBUTABLE_POSITION"),
        (Notification.unattributable_fill(ALERT_ID, "conto-1", "SOL"), "UNATTRIBUTABLE_FILL"),
        (Notification.reconciliation_alarm(ALERT_ID, "test-1", usdc(1), usdc(2)), "RECONCILIATION_ALARM"),
        (Notification.cash_out_done(FLOW_ID, "alfa", usdc(1)), "CASH_OUT"),
        (Notification.emergency_closing_done(1, ("alfa",)), "EMERGENCY_CLOSING"),
    ],
)
def test_every_notification_carries_the_type_of_its_event(notification: Notification, event: str) -> None:
    assert notification.event is NotificationEvent[event]


def test_the_test_notification_is_no_event_of_a_flow_or_of_an_account() -> None:
    assert Notification.test().event is None
    assert Notification.test().flow is None


def test_a_notification_of_a_flow_names_its_flow() -> None:
    assert Notification.cash_out_done(FLOW_ID, "alfa", usdc(1)).flow == "alfa"


@pytest.mark.parametrize(
    "notification",
    [
        Notification.reconciliation_alarm(ALERT_ID, "test-1", usdc(1), usdc(2)),
        Notification.unattributable_fill(ALERT_ID, "test-1", "SOL"),
        Notification.emergency_closing_done(1, ("alfa", "beta")),
    ],
)
def test_a_notification_of_the_account_names_no_flow(notification: Notification) -> None:
    assert notification.flow is None


# ADR destinazioni-delle-notifiche-nella-dashboard: the pages each notification leads to (R3.5.6).

FLOW = NotificationTarget.flow(FLOW_ID)
ALERT = NotificationTarget.alert(ALERT_ID)


@pytest.mark.parametrize(
    ("notification", "targets"),
    [
        (
            Notification.position_opened(FLOW_ID, "alfa", "BTC", "long", 3, usdc(150)),
            (FLOW, NotificationTarget.open_position(FLOW_ID, "BTC")),
        ),
        (
            Notification.position_closed(FLOW_ID, "alfa", "ETH", usdc(1), "decisione dell'agente", CLOSED_AT),
            (FLOW, NotificationTarget.closed_position(FLOW_ID, "ETH", CLOSED_AT)),
        ),
        (
            Notification.position_closed(FLOW_ID, "alfa", "BTC", usdc(-1), "stop loss", CLOSED_AT),
            (FLOW, NotificationTarget.closed_position(FLOW_ID, "BTC", CLOSED_AT)),
        ),
        (
            Notification.position_closed(FLOW_ID, "alfa", "BTC", usdc(-1), "liquidazione", CLOSED_AT),
            (FLOW, NotificationTarget.closed_position(FLOW_ID, "BTC", CLOSED_AT)),
        ),
        (Notification.cycle_failed(FLOW_ID, "alfa", "timeout"), (FLOW,)),
        (Notification.order_rejected(FLOW_ID, "alfa", "rifiutato"), (FLOW,)),
        (Notification.flow_paused(FLOW_ID, "alfa", "credito esaurito", ALERT_ID), (ALERT, FLOW)),
        (Notification.openings_suspended(FLOW_ID, "alfa", "perdita"), (FLOW,)),
        (Notification.opening_reduced(FLOW_ID, "alfa", "BTC", usdc(2), usdc(1)), (FLOW,)),
        (Notification.opening_blocked(FLOW_ID, "alfa", "BTC", "motivo"), (FLOW,)),
        (Notification.cash_out_done(FLOW_ID, "alfa", usdc(118)), (FLOW,)),
        (
            Notification.unattributable_position(ALERT_ID, "conto-1", "SOL"),
            (ALERT,),
        ),
        (
            Notification.unattributable_fill(ALERT_ID, "conto-1", "SOL"),
            (ALERT,),
        ),
        (
            Notification.reconciliation_alarm(ALERT_ID, "conto-1", usdc(980), usdc(1000)),
            (ALERT,),
        ),
        (Notification.emergency_closing_done(2, ["alfa"]), ()),
        (Notification.test(), ()),
    ],
)
def test_each_notification_leads_to_the_pages_it_is_about(
    notification: Notification, targets: tuple[NotificationTarget, ...]
) -> None:
    assert notification.targets == targets


def test_the_flow_of_a_notification_is_found_by_its_id() -> None:
    assert Notification.cycle_failed(FLOW_ID, "alfa", "timeout").flow_id == FLOW_ID


@pytest.mark.parametrize(
    "notification",
    [
        Notification.unattributable_position(ALERT_ID, "conto-1", "SOL"),
        Notification.emergency_closing_done(2, ["alfa"]),
        Notification.test(),
    ],
)
def test_a_notification_of_no_single_flow_has_no_flow_id(notification: Notification) -> None:
    assert notification.flow_id is None


def test_the_state_of_the_flow_keeps_the_pages_of_the_notification() -> None:
    notification = Notification.cycle_failed(FLOW_ID, "alfa", "timeout").with_flow_status(STATUS)

    assert notification.targets == (FLOW,)


def test_a_flow_paused_leads_to_its_alert_and_still_names_its_flow() -> None:
    assert Notification.flow_paused(FLOW_ID, "alfa", "credito esaurito", ALERT_ID).flow_id == FLOW_ID
