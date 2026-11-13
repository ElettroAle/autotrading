"""What the flows, their cycles and their orders tell the user, through the notifier of the tenant (R1.8.2)."""

from decimal import Decimal

from autotrading.application.notifications.notify_cycle_failed import NotifyCycleFailedUseCase
from autotrading.application.notifications.notify_flow_paused import NotifyFlowPausedUseCase
from autotrading.application.notifications.notify_order_rejected import NotifyOrderRejectedUseCase
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.notifications.notify_position_opened import NotifyPositionOpenedUseCase
from autotrading.domain.notifications.notification import Notification


class Notifier:
    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def execute(self, notification: Notification) -> None:
        self.sent.append(notification)


def test_a_flow_paused_on_its_own_is_told_with_the_reason() -> None:
    notifier = Notifier()

    NotifyFlowPausedUseCase(notifier).execute("alfa", "credito esaurito")

    assert notifier.sent == [Notification.flow_paused("alfa", "credito esaurito")]


def test_a_failed_cycle_is_told_with_the_message_of_its_error() -> None:
    notifier = Notifier()

    NotifyCycleFailedUseCase(notifier).execute("alfa", "timeout")

    assert notifier.sent == [Notification.cycle_failed("alfa", "timeout")]


def test_a_refused_order_is_told_with_the_message_of_the_exchange() -> None:
    notifier = Notifier()

    NotifyOrderRejectedUseCase(notifier).execute("alfa", "Insufficient margin")

    assert [notification.text for notification in notifier.sent] == ["alfa: ordine rifiutato, Insufficient margin"]


def test_an_opening_is_told_with_its_value_in_whole_units_of_the_settlement_currency() -> None:
    notifier = Notifier()

    NotifyPositionOpenedUseCase(notifier, "USDC").execute("alfa", "BTC", "long", 2, Decimal("99.6"))

    assert [notification.text for notification in notifier.sent] == ["alfa: aperta long BTC, leva 2, 100 USDC"]


def test_a_closing_is_told_with_its_pnl_in_the_settlement_currency() -> None:
    notifier = Notifier()

    NotifyPositionClosedUseCase(notifier, "USDC").execute("alfa", "BTC", Decimal("1.5"))

    assert [notification.text for notification in notifier.sent] == ["alfa: chiusa BTC, PnL 1,50 USDC"]
