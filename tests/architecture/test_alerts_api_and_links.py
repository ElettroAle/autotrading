"""ADR-api-degli-avvisi-e-link-nelle-notifiche: the API exposes the list, the number of the open alerts, the detail and
the resolution by hand; the notification of an alert leads to its detail, and only the adapter of the dashboard knows
the route.
"""

import inspect
from uuid import uuid4

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.outbound.dashboard.notification_links import DashboardNotificationLinkAdapter
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_target import NotificationTarget, TargetKind
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.support.architecture import source_modules
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform

DASHBOARD = "https://autotrading.example/dashboard"
ROUTES = {
    ("GET", "/alerts"),
    ("GET", "/alerts/summary"),
    ("GET", "/alerts/{alert_id}"),
    ("POST", "/alerts/{alert_id}/resolution"),
}
LINKS_ADAPTER = "adapters/outbound/dashboard/notification_links.py"
NOTICES = (
    Notification.flow_paused,
    Notification.reconciliation_alarm,
    Notification.unattributable_fill,
    Notification.unattributable_position,
)


def test_adr_api_degli_avvisi_the_api_exposes_list_summary_detail_and_resolution() -> None:
    api = create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(InMemoryTenantRepositoryAdapter()),
        Platform().for_tenant,
        IdentityProvider().authentication(),
    )
    paths = api.openapi()["paths"]

    routes = {(method.upper(), path) for path, operations in paths.items() for method in operations}

    assert {route for route in routes if route[1].startswith("/alerts")} == ROUTES


def test_adr_api_degli_avvisi_the_link_of_an_alert_leads_to_its_detail() -> None:
    alert_id = uuid4()

    link = DashboardNotificationLinkAdapter(DASHBOARD).link(NotificationTarget.alert(alert_id))

    assert link is not None
    assert (link.label, link.url) == ("Apri avviso", f"{DASHBOARD}/alerts/{alert_id}")


def test_adr_api_degli_avvisi_no_notification_leads_to_the_alarms_of_an_account_any_more() -> None:
    assert "account_alarms" not in {kind.value for kind in TargetKind}
    assert all("alert_id" in inspect.signature(notice).parameters for notice in NOTICES)


def test_adr_api_degli_avvisi_only_the_adapter_of_the_dashboard_knows_the_route_of_an_alert() -> None:
    knowing = {module.path for module in source_modules() if '"/alerts/' in module.text or "/alerts/{" in module.text}

    assert knowing - {"adapters/inbound/api/alerts.py"} == {LINKS_ADAPTER}
