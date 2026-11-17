from decimal import Decimal

import pytest

from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.errors import InvalidNotificationError
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Amount, Notification
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned


@pytest.mark.parametrize(
    ("notification", "text"),
    [
        (
            Notification.position_opened("alfa", "BTC", "long", 3, Amount(Decimal(150), "USDC")),
            "alfa: aperta long BTC, leva 3, 150 USDC",
        ),
        (
            Notification.position_closed("alfa", "BTC", Amount(Decimal("4.20"), "USDC"), "decisione dell'agente"),
            "alfa: chiusa BTC, PnL 4,20 USDC",
        ),
        (
            Notification.position_closed("alfa", "ETH", Amount(Decimal("-0.5"), "USDC"), "comando manuale"),
            "alfa: chiusa ETH, PnL -0,50 USDC",
        ),
        (
            Notification.position_closed("alfa", "BTC", Amount(Decimal("-5.1"), "USDC"), "stop loss"),
            "alfa: chiusa BTC per stop loss, PnL -5,10 USDC",
        ),
        (
            Notification.position_closed("alfa", "BTC", Amount(Decimal("4.9"), "USDC"), "take profit"),
            "alfa: chiusa BTC per take profit, PnL 4,90 USDC",
        ),
        (
            Notification.position_closed("alfa", "BTC", Amount(Decimal("-48.5"), "USDC"), "liquidazione"),
            "alfa: liquidata BTC, PnL -48,50 USDC",
        ),
        (
            Notification.position_liquidated("alfa", "BTC", Amount(Decimal(-48), "USDC")),
            "alfa: liquidata BTC, PnL -48 USDC",
        ),
        (
            Notification.opening_reduced("alfa", "BTC", Amount(Decimal(150), "USDC"), Amount(Decimal(100), "USDC")),
            "alfa: apertura BTC ridotta da 150 a 100 USDC",
        ),
        (
            Notification.opening_blocked("alfa", "BTC", "confidenza 40 sotto la minima 60"),
            "alfa: apertura BTC non eseguita, confidenza 40 sotto la minima 60",
        ),
        (Notification.cash_out_done("alfa", Amount(Decimal(118), "USDC")), "alfa: incassati 118 USDC"),
        (
            Notification.emergency_closing_done(1, ("alfa",)),
            "chiusura di emergenza: 1 posizione chiusa, alfa in pausa",
        ),
        (
            Notification.emergency_closing_done(3, ("alfa", "beta")),
            "chiusura di emergenza: 3 posizioni chiuse, alfa, beta in pausa",
        ),
        (
            Notification.emergency_closing_done(0, ()),
            "chiusura di emergenza: 0 posizioni chiuse, nessun flusso in pausa",
        ),
        (Notification.cycle_failed("alfa", "timeout"), "alfa: ciclo fallito, timeout"),
        (Notification.order_rejected("alfa", "Order rejected"), "alfa: ordine rifiutato, Order rejected"),
        (
            Notification.flow_paused("alfa", "credito esaurito presso openrouter"),
            "alfa: in pausa, credito esaurito presso openrouter",
        ),
        (
            Notification.openings_suspended("alfa", "perdita giornaliera 6% oltre il 5%"),
            "alfa: aperture sospese, perdita giornaliera 6% oltre il 5%",
        ),
        (Notification.unattributable_position("conto-1", "SOL"), "conto-1: posizione non attribuibile su SOL"),
        (Notification.unattributable_fill("conto-1", "ETH"), "conto-1: esecuzione non attribuibile su ETH"),
        (
            Notification.unattributable_movement("conto-1", Amount(Decimal("12.5"), "USDC")),
            "conto-1: movimento non attribuibile di 12,50 USDC",
        ),
        (
            Notification.reconciliation_alarm("test-1", Amount(Decimal(980), "USDC"), Amount(Decimal(1000), "USDC")),
            "test-1: allarme di riconciliazione, saldo 980 USDC invece di 1000 USDC",
        ),
    ],
)
def test_each_event_names_its_subject_and_its_essential_values(notification: Notification, text: str) -> None:
    assert notification.text == text


def test_an_amount_never_turns_into_an_exponent() -> None:
    assert str(Amount(Decimal("1E+2"), "USDC")) == "100 USDC"


@pytest.mark.parametrize("subject", ["", "  "])
def test_a_notification_without_its_subject_is_a_defect(subject: str) -> None:
    with pytest.raises(InvalidNotificationError, match=r"^notifica senza flusso o conto$"):
        Notification.cycle_failed(subject, "timeout")


def test_a_linked_chat_belongs_to_its_tenant() -> None:
    tenant = TenantId.new()
    chat = LinkedChat(tenant, ChatId(-100123))

    assert (chat.tenant_id, chat.chat_id.value) == (tenant, -100123)
    assert isinstance(chat, TenantOwned)


def test_the_test_notification_says_where_the_notifications_arrive() -> None:
    assert Notification.test().text == "notifica di prova: le notifiche dei tuoi flussi arrivano qui"


def test_an_opening_is_told_by_its_value_in_whole_units() -> None:
    notification = Notification.position_opened("alfa", "BTC", "long", 3, Amount(Decimal("20.006"), "USDC"))

    assert notification.text == "alfa: aperta long BTC, leva 3, 20 USDC"


@pytest.mark.parametrize(
    ("notification", "subject"),
    [
        (Notification.flow_paused("alfa", "credito esaurito"), "alfa: in pausa"),
        (Notification.cycle_failed("alfa", "timeout, riprova"), "alfa: ciclo fallito"),
        (Notification.unattributable_position("conto-1", "SOL"), "conto-1: posizione non attribuibile su SOL"),
        (Notification.test(), "AutoTrading: prova delle notifiche"),
    ],
)
def test_the_subject_of_an_email_names_the_flow_or_account_and_the_event_without_its_details(
    notification: Notification, subject: str
) -> None:
    assert notification.email_subject == subject


def test_the_text_of_an_email_is_the_text_of_the_notification() -> None:
    notification = Notification.flow_paused("alfa", "credito esaurito")

    assert notification.text == "alfa: in pausa, credito esaurito"


@pytest.mark.parametrize(
    ("notification", "event"),
    [
        (Notification.position_opened("alfa", "BTC", "long", 3, Amount(Decimal(150), "USDC")), "POSITION_OPENED"),
        (Notification.position_closed("alfa", "BTC", Amount(Decimal(1), "USDC"), "stop del flusso"), "POSITION_CLOSED"),
        (Notification.position_closed("alfa", "BTC", Amount(Decimal(1), "USDC"), "stop loss"), "STOP_LOSS"),
        (Notification.position_closed("alfa", "BTC", Amount(Decimal(1), "USDC"), "take profit"), "TAKE_PROFIT"),
        (Notification.position_closed("alfa", "BTC", Amount(Decimal(1), "USDC"), "liquidazione"), "LIQUIDATION"),
        (Notification.position_liquidated("alfa", "BTC", Amount(Decimal(1), "USDC")), "LIQUIDATION"),
        (Notification.cycle_failed("alfa", "timeout"), "CYCLE_FAILED"),
        (Notification.order_rejected("alfa", "rifiutato"), "ORDER_REJECTED"),
        (Notification.flow_paused("alfa", "credito esaurito"), "FLOW_PAUSED"),
        (Notification.openings_suspended("alfa", "perdita giornaliera 6% oltre il 5%"), "MAXIMUM_LOSS"),
        (
            Notification.opening_reduced("alfa", "BTC", Amount(Decimal(2), "USDC"), Amount(Decimal(1), "USDC")),
            "OPENING_REDUCED",
        ),
        (Notification.opening_blocked("alfa", "BTC", "motivo"), "OPENING_BLOCKED"),
        (Notification.unattributable_position("conto-1", "SOL"), "UNATTRIBUTABLE_POSITION"),
        (Notification.unattributable_fill("conto-1", "SOL"), "UNATTRIBUTABLE_FILL"),
        (Notification.unattributable_movement("conto-1", Amount(Decimal(1), "USDC")), "UNATTRIBUTABLE_MOVEMENT"),
        (
            Notification.reconciliation_alarm("test-1", Amount(Decimal(1), "USDC"), Amount(Decimal(2), "USDC")),
            "RECONCILIATION_ALARM",
        ),
        (Notification.cash_out_done("alfa", Amount(Decimal(1), "USDC")), "CASH_OUT"),
        (Notification.emergency_closing_done(1, ("alfa",)), "EMERGENCY_CLOSING"),
    ],
)
def test_every_notification_carries_the_type_of_its_event(notification: Notification, event: str) -> None:
    assert notification.kind is NotificationEvent[event]


def test_the_test_notification_is_no_event_of_a_flow_or_of_an_account() -> None:
    assert Notification.test().kind is None
    assert Notification.test().flow is None


def test_a_notification_of_a_flow_names_its_flow() -> None:
    assert Notification.cash_out_done("alfa", Amount(Decimal(1), "USDC")).flow == "alfa"


@pytest.mark.parametrize(
    "notification",
    [
        Notification.reconciliation_alarm("test-1", Amount(Decimal(1), "USDC"), Amount(Decimal(2), "USDC")),
        Notification.unattributable_fill("test-1", "SOL"),
        Notification.emergency_closing_done(1, ("alfa", "beta")),
    ],
)
def test_a_notification_of_the_account_names_no_flow(notification: Notification) -> None:
    assert notification.flow is None
