"""ADR notifiche-nell-app-salvate-per-tenant: the bell of the tenant through the API, the number of the unread
notifications, and their reading one by one or all at once (R6.2.1)."""

import base64
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.notification_inbox import inbox_cursor_of, inbox_cursor_text
from autotrading.application.notifications.errors import InboxCursorInvalidError
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.notifications.inbox_page import INBOX_PAGE_SIZE, InboxCursor
from autotrading.domain.notifications.notification import Amount, Notification
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
NINE = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)
FLOW, ALERT = uuid4(), uuid4()


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.now = NINE
    return platform


@pytest.fixture
def client_of(platform: Platform) -> Client:
    provider = IdentityProvider()
    api = create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(platform.tenants),
        platform.for_tenant,
        provider.authentication(),
    )

    def client(user: str) -> TestClient:
        person = platform.directory.person(user)
        person.roles.add("Utente")
        return TestClient(api, headers={"Authorization": f"Bearer {provider.token_for(person)}"})

    return client


def notified(platform: Platform, user: str, notification: Notification, minutes: int = 0) -> None:
    platform.inbox_of(platform.tenant_of(user)).add(notification, NINE + timedelta(minutes=minutes))


def test_the_bell_lists_the_notifications_newest_first_with_their_pages(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    closed_at = NINE - timedelta(hours=1)
    closing = Notification.position_closed(FLOW, "alfa", "BTC", Amount(Decimal(12), "USDC"), "agente", closed_at)
    notified(platform, "anna", Notification.flow_paused(FLOW, "alfa", "credito esaurito", ALERT))
    notified(platform, "anna", closing, 1)

    response = client.get("/notifications/inbox")

    assert response.status_code == 200
    body = response.json()
    assert body["next"] is None
    newest, paused = body["items"]
    assert {key: newest[key] for key in ("icon", "title", "text", "notified_at", "read_at")} == {
        "icon": closing.icon,
        "title": "alfa: posizione chiusa",
        "text": "Asset: BTC\nPnL: 12 USDC",
        "notified_at": "2026-11-19T09:01:00Z",
        "read_at": None,
    }
    assert newest["targets"] == [
        {
            "kind": "flow",
            "label": "Apri flusso",
            "flow_id": str(FLOW),
            "asset": None,
            "closed_at": None,
            "alert_id": None,
        },
        {
            "kind": "closed_position",
            "label": "Apri operazione",
            "flow_id": str(FLOW),
            "asset": "BTC",
            "closed_at": "2026-11-19T08:00:00Z",
            "alert_id": None,
        },
    ]
    assert paused["targets"][0] == {
        "kind": "alert",
        "label": "Apri avviso",
        "flow_id": None,
        "asset": None,
        "closed_at": None,
        "alert_id": str(ALERT),
    }


def test_the_bell_goes_by_pages_with_the_cursor_of_the_previous_one(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    for minute in range(INBOX_PAGE_SIZE + 1):
        notified(platform, "anna", Notification.cycle_failed(FLOW, f"flusso-{minute}", "timeout"), minute)

    first = client.get("/notifications/inbox").json()
    rest = client.get("/notifications/inbox", params={"cursor": first["next"]}).json()

    assert len(first["items"]) == INBOX_PAGE_SIZE
    assert [item["title"] for item in rest["items"]] == ["flusso-0: ciclo fallito"]
    assert rest["next"] is None


def test_a_cursor_the_list_never_gave_is_a_bad_request(client_of: Client) -> None:
    response = client_of("anna").get("/notifications/inbox", params={"cursor": "non-un-cursore"})

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "cursore delle notifiche non valido"}


def test_the_summary_counts_the_unread_notifications(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    notified(platform, "anna", Notification.test())
    notified(platform, "anna", Notification.cycle_failed(FLOW, "alfa", "timeout"), 1)

    assert client.get("/notifications/inbox/summary").json() == {"unread_count": 2}


def test_one_notification_is_read_and_the_others_stay_unread(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    notified(platform, "anna", Notification.test())
    notified(platform, "anna", Notification.cycle_failed(FLOW, "alfa", "timeout"), 1)
    newest = client.get("/notifications/inbox").json()["items"][0]

    response = client.post(f"/notifications/inbox/{newest['id']}/read")

    assert response.status_code == 204
    items = client.get("/notifications/inbox").json()["items"]
    assert [item["read_at"] is None for item in items] == [False, True]
    assert client.get("/notifications/inbox/summary").json() == {"unread_count": 1}


def test_every_notification_is_read_at_once(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    notified(platform, "anna", Notification.test())
    notified(platform, "anna", Notification.cycle_failed(FLOW, "alfa", "timeout"), 1)

    response = client.post("/notifications/inbox/read")

    assert response.status_code == 204
    assert client.get("/notifications/inbox/summary").json() == {"unread_count": 0}


def test_a_notification_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    notified(platform, "bruno", Notification.test())
    theirs = client_of("bruno").get("/notifications/inbox").json()["items"][0]

    response = client_of("anna").post(f"/notifications/inbox/{theirs['id']}/read")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "notifica non trovata"}
    assert client_of("anna").get("/notifications/inbox").json()["items"] == []
    assert client_of("bruno").get("/notifications/inbox/summary").json() == {"unread_count": 1}


def test_the_cursor_reads_back_as_the_place_it_marks() -> None:
    cursor = InboxCursor(NINE, uuid4())

    assert inbox_cursor_of(inbox_cursor_text(cursor)) == cursor


@pytest.mark.parametrize("text", ["%%%", base64.urlsafe_b64encode(b"senza-separatore").decode()])
def test_a_text_that_is_not_a_cursor_is_invalid(text: str) -> None:
    with pytest.raises(InboxCursorInvalidError):
        inbox_cursor_of(text)
