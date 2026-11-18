"""ADR destinazioni-delle-notifiche-nella-dashboard: every notification declares the pages it leads to (R3.5.6)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from autotrading.domain.notifications.errors import InvalidNotificationTargetError
from autotrading.domain.notifications.notification_link import NotificationLink
from autotrading.domain.notifications.notification_target import NotificationTarget, TargetKind

FLOW_ID = uuid4()
CLOSED_AT = datetime(2026, 11, 17, 10, 15, tzinfo=UTC)


@pytest.mark.parametrize(
    ("target", "kind", "label"),
    [
        (NotificationTarget.flow(FLOW_ID), TargetKind.FLOW, "Apri flusso"),
        (NotificationTarget.open_position(FLOW_ID, "BTC"), TargetKind.OPEN_POSITION, "Apri operazione"),
        (NotificationTarget.closed_position(FLOW_ID, "BTC", CLOSED_AT), TargetKind.CLOSED_POSITION, "Apri operazione"),
        (NotificationTarget.alert(FLOW_ID), TargetKind.ALERT, "Apri avviso"),
    ],
)
def test_each_target_is_of_its_kind_with_the_label_of_its_link(
    target: NotificationTarget, kind: TargetKind, label: str
) -> None:
    assert target.kind is kind
    assert target.owner_id == FLOW_ID
    assert target.label == label


def test_a_closed_position_is_found_by_its_asset_and_the_instant_it_closed() -> None:
    target = NotificationTarget.closed_position(FLOW_ID, "BTC", CLOSED_AT)

    assert (target.asset, target.closed_at) == ("BTC", CLOSED_AT)


def test_an_open_position_is_found_by_its_asset() -> None:
    target = NotificationTarget.open_position(FLOW_ID, "ETH")

    assert (target.asset, target.closed_at) == ("ETH", None)


@pytest.mark.parametrize(
    ("kind", "asset", "closed_at"),
    [
        (TargetKind.OPEN_POSITION, None, None),
        (TargetKind.OPEN_POSITION, " ", None),
        (TargetKind.CLOSED_POSITION, "BTC", None),
        (TargetKind.CLOSED_POSITION, None, CLOSED_AT),
        (TargetKind.CLOSED_POSITION, "BTC", datetime(2026, 11, 17, 10, 15)),
    ],
)
def test_a_position_without_what_finds_it_is_a_defect(
    kind: TargetKind, asset: str | None, closed_at: datetime | None
) -> None:
    with pytest.raises(InvalidNotificationTargetError, match=r"^destinazione della notifica senza la posizione$"):
        NotificationTarget(kind, FLOW_ID, asset, closed_at)


def test_a_link_reads_its_label_and_address() -> None:
    link = NotificationLink("Apri flusso", "https://example.org/dashboard/flows/1")

    assert (link.label, link.url) == ("Apri flusso", "https://example.org/dashboard/flows/1")
