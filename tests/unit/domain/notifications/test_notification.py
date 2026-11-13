from decimal import Decimal

import pytest

from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.errors import InvalidNotificationError
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Amount, Notification
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
            Notification.position_closed("alfa", "BTC", Amount(Decimal("4.20"), "USDC")),
            "alfa: chiusa BTC, PnL 4,20 USDC",
        ),
        (
            Notification.position_closed("alfa", "ETH", Amount(Decimal("-0.5"), "USDC")),
            "alfa: chiusa ETH, PnL -0,50 USDC",
        ),
        (Notification.cycle_failed("alfa", "timeout"), "alfa: ciclo fallito, timeout"),
        (Notification.order_rejected("alfa", "Order rejected"), "alfa: ordine rifiutato, Order rejected"),
        (
            Notification.flow_paused("alfa", "credito esaurito presso openrouter"),
            "alfa: in pausa, credito esaurito presso openrouter",
        ),
        (Notification.unattributable_position("conto-1", "SOL"), "conto-1: posizione non attribuibile su SOL"),
        (Notification.unattributable_fill("conto-1", "ETH"), "conto-1: esecuzione non attribuibile su ETH"),
        (
            Notification.unattributable_movement("conto-1", Amount(Decimal("12.5"), "USDC")),
            "conto-1: movimento non attribuibile di 12,50 USDC",
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
