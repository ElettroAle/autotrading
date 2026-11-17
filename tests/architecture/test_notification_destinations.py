"""ADR-destinazioni-delle-notifiche-nella-dashboard: every notification declares where it leads in the dashboard, and
only the dashboard folder knows the routes of the dashboard and its address. Domain and application name targets,
never pages; every other adapter receives the links already made.
"""

import inspect
import re

from autotrading.adapters.outbound.dashboard.notification_links import DashboardNotificationLinkAdapter
from autotrading.application.notifications import notify, ports
from autotrading.application.notifications.ports import NotificationLinkPort
from tests.support.architecture import source_modules

DASHBOARD_FOLDER = "adapters/outbound/dashboard/"
# The pages a notification leads to and the setting with the address of the dashboard: the API serves no page with a
# query, nor the alarms of one account.
DASHBOARD_ROUTE = re.compile(r"/positions\?|/closed-positions\?|\}/alarms\b|DASHBOARD_URL")

ROUTE_IN_THE_MESSENGER = """
def _message_body(chat_id, text, flow_id):
    return {"chat_id": chat_id, "text": text, "url": f"{BASE}/flows/{flow_id}/positions?asset=BTC"}
"""
TARGET_IN_THE_MESSENGER = """
def _message_body(chat_id, text, links):
    return {"chat_id": chat_id, "text": text, "buttons": [link.url for link in links]}
"""


def dashboard_routes_in(text: str) -> list[str]:
    """The routes of the dashboard, or the name of its address, that the text writes."""
    return DASHBOARD_ROUTE.findall(text)


def test_adr_destinazioni_delle_notifiche_only_the_dashboard_folder_knows_its_routes_and_its_address() -> None:
    found = {
        module.path: routes
        for module in source_modules()
        if not module.path.startswith(DASHBOARD_FOLDER) and (routes := dashboard_routes_in(module.text))
    }

    assert found == {}


def test_adr_destinazioni_delle_notifiche_a_route_written_outside_the_dashboard_folder_is_found() -> None:
    assert dashboard_routes_in(ROUTE_IN_THE_MESSENGER) == ["/positions?"]
    assert dashboard_routes_in(TARGET_IN_THE_MESSENGER) == []
    assert dashboard_routes_in('source.optional("DASHBOARD_URL")') == ["DASHBOARD_URL"]
    assert dashboard_routes_in('f"/accounts/{account_id}/alarms"') == ["}/alarms"]
    assert dashboard_routes_in('@router.get("/flows/{flow_id}/closed-positions")') == []
    assert dashboard_routes_in('@router.get("/reconciliation/alarms")') == []


def test_adr_destinazioni_delle_notifiche_the_dashboard_adapter_realizes_the_port_of_the_links() -> None:
    adapter: NotificationLinkPort = DashboardNotificationLinkAdapter(None)

    assert adapter.link.__name__ == "link"
    assert "NotificationLinkPort" in vars(ports)


def test_adr_destinazioni_delle_notifiche_the_notification_names_its_flow_by_its_id_never_by_its_name() -> None:
    source = inspect.getsource(notify)

    assert "flow_id" in source
    assert ".list()" not in source
    assert "notification.flow ==" not in source
