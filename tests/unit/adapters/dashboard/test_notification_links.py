"""ADR destinazioni-delle-notifiche-nella-dashboard: the pages of the dashboard a notification leads to, on the address
the installation declares (R3.5.6).
"""

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.dashboard.composition import dashboard_adapters
from autotrading.adapters.outbound.dashboard.notification_links import DashboardNotificationLinkAdapter
from autotrading.domain.notifications.notification_link import NotificationLink
from autotrading.domain.notifications.notification_target import NotificationTarget

DASHBOARD = "https://autotrading-dev.example.ts.net/dashboard"
FLOW_ID = UUID("4f6c1d0e-7a3b-4e59-9c2d-1b8e5f0a6c71")
ACCOUNT_ID = UUID("0b1c2d3e-4f50-4a61-8b72-93a4b5c6d7e8")
CLOSED_AT = datetime(2026, 11, 17, 10, 15, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("target", "link"),
    [
        (NotificationTarget.flow(FLOW_ID), NotificationLink("Apri flusso", f"{DASHBOARD}/flows/{FLOW_ID}")),
        (
            NotificationTarget.open_position(FLOW_ID, "BTC"),
            NotificationLink("Apri operazione", f"{DASHBOARD}/flows/{FLOW_ID}/positions?asset=BTC"),
        ),
        (
            NotificationTarget.closed_position(FLOW_ID, "BTC", CLOSED_AT),
            NotificationLink(
                "Apri operazione",
                f"{DASHBOARD}/flows/{FLOW_ID}/closed-positions?asset=BTC&closed_at=2026-11-17T10%3A15%3A30%2B00%3A00",
            ),
        ),
        (
            NotificationTarget.account_alarms(ACCOUNT_ID),
            NotificationLink("Apri allarmi", f"{DASHBOARD}/accounts/{ACCOUNT_ID}/alarms"),
        ),
    ],
)
def test_each_target_leads_to_its_page_of_the_dashboard(target: NotificationTarget, link: NotificationLink) -> None:
    assert DashboardNotificationLinkAdapter(DASHBOARD).link(target) == link


def test_the_instant_of_a_closing_is_told_in_utc() -> None:
    rome = timezone(timedelta(hours=1))
    target = NotificationTarget.closed_position(FLOW_ID, "BTC", datetime(2026, 11, 17, 11, 15, 30, tzinfo=rome))

    link = DashboardNotificationLinkAdapter(DASHBOARD).link(target)

    assert link is not None
    assert link.url.endswith("closed_at=2026-11-17T10%3A15%3A30%2B00%3A00")


def test_an_asset_with_reserved_characters_is_encoded() -> None:
    link = DashboardNotificationLinkAdapter(DASHBOARD).link(NotificationTarget.open_position(FLOW_ID, "kBONK&x"))

    assert link is not None
    assert link.url.endswith("/positions?asset=kBONK%26x")


def test_without_a_dashboard_no_target_leads_anywhere() -> None:
    assert DashboardNotificationLinkAdapter(None).link(NotificationTarget.flow(FLOW_ID)) is None


@pytest.mark.parametrize("address", [DASHBOARD, f"{DASHBOARD}/"])
def test_the_adapter_reads_the_address_of_the_dashboard_of_the_installation(address: str) -> None:
    adapter = dashboard_adapters(ConfigurationSource({"DASHBOARD_URL": address}))

    assert adapter.link(NotificationTarget.flow(FLOW_ID)) == NotificationLink(
        "Apri flusso", f"{DASHBOARD}/flows/{FLOW_ID}"
    )


def test_an_installation_without_a_dashboard_sends_notifications_without_links() -> None:
    adapter = dashboard_adapters(ConfigurationSource({}))

    assert adapter.link(NotificationTarget.flow(FLOW_ID)) is None


@pytest.mark.parametrize("address", ["autotrading-dev/dashboard", "ftp://example.org/dashboard", "https://"])
def test_an_address_that_is_no_web_address_stops_the_worker(address: str) -> None:
    with pytest.raises(InvalidConfigurationError, match=r"^configurazione non valida: DASHBOARD_URL$"):
        dashboard_adapters(ConfigurationSource({"DASHBOARD_URL": address}))
