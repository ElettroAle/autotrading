"""ADR stato-del-flusso-in-ogni-notifica: every notification of a flow closes with the state of the flow."""

import logging
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.domain.notifications.flow_status import (
    FlowStatusFigures,
    FlowStatusLine,
    NotifiedFlowStatus,
    RecordedEquity,
)
from autotrading.domain.notifications.notification import Amount, Notification
from tests.fakes.flow_status import FakeFlowStatusAdapter

ALFA = FlowStatusFigures(
    NotifiedFlowStatus.ACTIVE, 2, "USDC", RecordedEquity(Decimal("312.40"), Decimal(300), Decimal(0))
)
OPENED = Notification.position_opened(uuid4(), "alfa", "BTC", "long", 3, Amount(Decimal(150), "USDC"))


class Notifier:
    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def execute(self, notification: Notification) -> None:
        self.sent.append(notification)


@pytest.fixture
def flow_status() -> FakeFlowStatusAdapter:
    flow_status = FakeFlowStatusAdapter()
    flow_status.figures["alfa"] = ALFA
    return flow_status


def test_a_notification_of_a_flow_closes_with_the_state_of_the_flow(flow_status: FakeFlowStatusAdapter) -> None:
    notifier = Notifier()

    NotifyFlowEventUseCase(notifier, flow_status).execute(OPENED)

    assert notifier.sent == [OPENED.with_flow_status(FlowStatusLine.of(ALFA))]
    assert flow_status.asked == ["alfa"]


def test_a_notification_of_the_account_reads_no_state(flow_status: FakeFlowStatusAdapter) -> None:
    notifier = Notifier()
    alarm = Notification.unattributable_fill(uuid4(), "test-1", "SOL")

    NotifyFlowEventUseCase(notifier, flow_status).execute(alarm)

    assert notifier.sent == [alarm]
    assert flow_status.asked == []


def test_a_flow_no_longer_found_leaves_its_notification_without_state(flow_status: FakeFlowStatusAdapter) -> None:
    notifier = Notifier()
    paused = Notification.flow_paused(uuid4(), "beta", "credito esaurito")

    NotifyFlowEventUseCase(notifier, flow_status).execute(paused)

    assert notifier.sent == [paused]


def test_a_state_not_read_is_recorded_and_the_notification_leaves_without_it(
    flow_status: FakeFlowStatusAdapter, caplog: pytest.LogCaptureFixture
) -> None:
    notifier = Notifier()
    flow_status.readable = False

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        NotifyFlowEventUseCase(notifier, flow_status).execute(OPENED)

    assert notifier.sent == [OPENED]
    [record] = caplog.records
    assert record.getMessage() == "stato del flusso non letto per la notifica"
    assert record.__dict__["flow"] == "alfa"
