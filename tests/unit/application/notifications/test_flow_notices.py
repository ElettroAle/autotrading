"""What the flows, their cycles and their orders tell the user, through the notifier of the tenant (R1.8.2); the
notices of a flow close with the state of the flow (ADR stato-del-flusso-in-ogni-notifica).
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from autotrading.application.notifications.notify_cash_out_done import NotifyCashOutDoneUseCase
from autotrading.application.notifications.notify_cycle_failed import NotifyCycleFailedUseCase
from autotrading.application.notifications.notify_emergency_closing_done import NotifyEmergencyClosingDoneUseCase
from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.application.notifications.notify_flow_paused import NotifyFlowPausedUseCase
from autotrading.application.notifications.notify_opening_blocked import NotifyOpeningBlockedUseCase
from autotrading.application.notifications.notify_opening_reduced import NotifyOpeningReducedUseCase
from autotrading.application.notifications.notify_openings_suspended import NotifyOpeningsSuspendedUseCase
from autotrading.application.notifications.notify_order_rejected import NotifyOrderRejectedUseCase
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.notifications.notify_position_opened import NotifyPositionOpenedUseCase
from autotrading.application.notifications.notify_reconciliation_alarm import NotifyReconciliationAlarmUseCase
from autotrading.application.notifications.notify_unattributable_fill import NotifyUnattributableFillUseCase
from autotrading.application.notifications.notify_unattributable_position import NotifyUnattributablePositionUseCase
from autotrading.domain.notifications.flow_status import (
    FlowStatusFigures,
    FlowStatusLine,
    NotifiedFlowStatus,
    RecordedEquity,
)
from autotrading.domain.notifications.notification import Amount, Notification
from tests.fakes.flow_status import FakeFlowStatusAdapter

FLOW_ID, ACCOUNT_ID = uuid4(), uuid4()
CLOSED_AT = datetime(2026, 11, 17, 10, 15, tzinfo=UTC)
ALFA = FlowStatusFigures(
    NotifiedFlowStatus.ACTIVE, 2, "USDC", RecordedEquity(Decimal("312.40"), Decimal(300), Decimal(0))
)
STATUS = FlowStatusLine.of(ALFA)


class Notifier:
    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def execute(self, notification: Notification) -> None:
        self.sent.append(notification)


def of_flow(notifier: Notifier) -> NotifyFlowEventUseCase:
    flow_status = FakeFlowStatusAdapter()
    flow_status.figures["alfa"] = ALFA
    return NotifyFlowEventUseCase(notifier, flow_status)


def texts(notifier: Notifier) -> list[str]:
    return [notification.text for notification in notifier.sent]


def test_openings_suspended_for_maximum_loss_are_told_with_the_threshold_passed() -> None:
    notifier = Notifier()

    NotifyOpeningsSuspendedUseCase(of_flow(notifier)).execute(FLOW_ID, "alfa", "perdita giornaliera 6% oltre il 5%")

    assert notifier.sent == [
        Notification.openings_suspended(FLOW_ID, "alfa", "perdita giornaliera 6% oltre il 5%").with_flow_status(STATUS)
    ]


def test_a_flow_paused_on_its_own_is_told_with_the_reason() -> None:
    notifier = Notifier()

    NotifyFlowPausedUseCase(of_flow(notifier)).execute(FLOW_ID, "alfa", "credito esaurito")

    assert notifier.sent == [Notification.flow_paused(FLOW_ID, "alfa", "credito esaurito").with_flow_status(STATUS)]


def test_a_failed_cycle_is_told_with_the_message_of_its_error() -> None:
    notifier = Notifier()

    NotifyCycleFailedUseCase(of_flow(notifier)).execute(FLOW_ID, "alfa", "timeout")

    assert notifier.sent == [Notification.cycle_failed(FLOW_ID, "alfa", "timeout").with_flow_status(STATUS)]


def test_a_refused_order_is_told_with_the_message_of_the_exchange() -> None:
    notifier = Notifier()

    NotifyOrderRejectedUseCase(of_flow(notifier)).execute(FLOW_ID, "alfa", "Insufficient margin")

    assert notifier.sent == [
        Notification.order_rejected(FLOW_ID, "alfa", "Insufficient margin").with_flow_status(STATUS)
    ]


def test_an_opening_is_told_with_its_value_in_whole_units_of_the_settlement_currency() -> None:
    notifier = Notifier()

    NotifyPositionOpenedUseCase(of_flow(notifier), "USDC").execute(FLOW_ID, "alfa", "BTC", "long", 2, Decimal("99.6"))

    assert texts(notifier) == [
        "\U0001f7e2 alfa: posizione aperta\n\nAsset: BTC\nDirezione: long\nLeva: 2\nValore: 100 USDC\n" + STATUS.text
    ]


def test_a_closing_is_told_with_its_pnl_in_the_settlement_currency() -> None:
    notifier = Notifier()

    NotifyPositionClosedUseCase(of_flow(notifier), "USDC").execute(
        FLOW_ID, "alfa", "BTC", Decimal("1.5"), "decisione dell'agente", CLOSED_AT
    )

    assert texts(notifier) == ["✅ alfa: posizione chiusa\n\nAsset: BTC\nPnL: 1,50 USDC\n" + STATUS.text]


def test_a_closing_by_a_protection_is_told_once_with_its_reason() -> None:
    notifier = Notifier()

    NotifyPositionClosedUseCase(of_flow(notifier), "USDC").execute(
        FLOW_ID, "alfa", "BTC", Decimal("-5.1"), "stop loss", CLOSED_AT
    )

    closing = Notification.position_closed(
        FLOW_ID, "alfa", "BTC", Amount(Decimal("-5.1"), "USDC"), "stop loss", CLOSED_AT
    )
    assert notifier.sent == [closing.with_flow_status(STATUS)]
    assert texts(notifier) == ["\U0001f6d1 alfa: chiusa per stop loss\n\nAsset: BTC\nPnL: -5,10 USDC\n" + STATUS.text]


def test_an_opening_reduced_by_the_risk_check_is_told_with_both_margins_in_the_settlement_currency() -> None:
    notifier = Notifier()

    NotifyOpeningReducedUseCase(of_flow(notifier), "USDC").execute(FLOW_ID, "alfa", "BTC", Decimal(150), Decimal(100))

    assert notifier.sent == [
        Notification.opening_reduced(
            FLOW_ID, "alfa", "BTC", Amount(Decimal(150), "USDC"), Amount(Decimal(100), "USDC")
        ).with_flow_status(STATUS)
    ]


def test_an_opening_blocked_by_the_risk_check_is_told_with_its_cause() -> None:
    notifier = Notifier()

    NotifyOpeningBlockedUseCase(of_flow(notifier)).execute(FLOW_ID, "alfa", "BTC", "confidenza 40 sotto la minima 60")

    assert notifier.sent == [
        Notification.opening_blocked(FLOW_ID, "alfa", "BTC", "confidenza 40 sotto la minima 60").with_flow_status(
            STATUS
        )
    ]


def test_a_cash_out_is_told_with_the_money_freed_in_the_settlement_currency() -> None:
    notifier = Notifier()

    NotifyCashOutDoneUseCase(of_flow(notifier), "USDC").execute(FLOW_ID, "alfa", Decimal(118))

    assert notifier.sent == [
        Notification.cash_out_done(FLOW_ID, "alfa", Amount(Decimal(118), "USDC")).with_flow_status(STATUS)
    ]


def test_an_emergency_closing_is_told_with_the_positions_closed_and_the_flows_paused() -> None:
    notifier = Notifier()

    NotifyEmergencyClosingDoneUseCase(notifier).execute(1, ["alfa"])

    assert notifier.sent == [Notification.emergency_closing_done(1, ("alfa",))]


def test_the_cases_no_flow_explains_are_told_by_the_name_of_the_account() -> None:
    notifier = Notifier()

    NotifyUnattributablePositionUseCase(notifier).execute(ACCOUNT_ID, "principale", "BTC")
    NotifyUnattributableFillUseCase(notifier).execute(ACCOUNT_ID, "principale", "ETH")

    assert notifier.sent == [
        Notification.unattributable_position(ACCOUNT_ID, "principale", "BTC"),
        Notification.unattributable_fill(ACCOUNT_ID, "principale", "ETH"),
    ]


def test_an_alarm_of_reconciliation_is_told_with_the_balances_in_the_settlement_currency() -> None:
    notifier = Notifier()

    NotifyReconciliationAlarmUseCase(notifier, "USDC").execute(ACCOUNT_ID, "test-1", Decimal("980.5"), Decimal(1000))

    assert texts(notifier) == [
        "\U0001f6a8 test-1: allarme di riconciliazione\n\nSaldo letto: 980,50 USDC\nSaldo atteso: 1000 USDC"
    ]
