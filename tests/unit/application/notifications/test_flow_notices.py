"""What the flows, their cycles and their orders tell the user, through the notifier of the tenant (R1.8.2)."""

from decimal import Decimal

from autotrading.application.notifications.notify_cycle_failed import NotifyCycleFailedUseCase
from autotrading.application.notifications.notify_flow_paused import NotifyFlowPausedUseCase
from autotrading.application.notifications.notify_openings_suspended import NotifyOpeningsSuspendedUseCase
from autotrading.application.notifications.notify_order_rejected import NotifyOrderRejectedUseCase
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.notifications.notify_position_opened import NotifyPositionOpenedUseCase
from autotrading.application.notifications.notify_reconciliation_alarm import NotifyReconciliationAlarmUseCase
from autotrading.application.notifications.notify_unattributable_fill import NotifyUnattributableFillUseCase
from autotrading.application.notifications.notify_unattributable_movement import NotifyUnattributableMovementUseCase
from autotrading.application.notifications.notify_unattributable_position import NotifyUnattributablePositionUseCase
from autotrading.domain.notifications.notification import Amount, Notification


class Notifier:
    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def execute(self, notification: Notification) -> None:
        self.sent.append(notification)


def test_openings_suspended_for_maximum_loss_are_told_with_the_threshold_passed() -> None:
    notifier = Notifier()

    NotifyOpeningsSuspendedUseCase(notifier).execute("alfa", "perdita giornaliera 6% oltre il 5%")

    assert notifier.sent == [Notification.openings_suspended("alfa", "perdita giornaliera 6% oltre il 5%")]


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


def test_the_cases_no_flow_explains_are_told_by_the_name_of_the_account() -> None:
    notifier = Notifier()

    NotifyUnattributablePositionUseCase(notifier).execute("principale", "BTC")
    NotifyUnattributableFillUseCase(notifier).execute("principale", "ETH")
    NotifyUnattributableMovementUseCase(notifier, "USDC").execute("principale", Decimal(-15))

    assert notifier.sent == [
        Notification.unattributable_position("principale", "BTC"),
        Notification.unattributable_fill("principale", "ETH"),
        Notification.unattributable_movement("principale", Amount(Decimal(-15), "USDC")),
    ]


def test_an_alarm_of_reconciliation_is_told_with_the_balances_in_the_settlement_currency() -> None:
    notifier = Notifier()

    NotifyReconciliationAlarmUseCase(notifier, "USDC").execute("test-1", Decimal("980.5"), Decimal(1000))

    assert [notification.text for notification in notifier.sent] == [
        "test-1: allarme di riconciliazione, saldo 980,50 USDC invece di 1000 USDC"
    ]
