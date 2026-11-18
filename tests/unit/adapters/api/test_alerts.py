"""ADR api-degli-avvisi-e-link-nelle-notifiche: the alerts of the tenant through the API, the number of the open ones,
the detail with the commands that resolve it, and the resolution by hand (R6.2.3)."""

import base64
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.alerts import alert_cursor_of, alert_cursor_text
from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.notifications.errors import AlertCursorInvalidError
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.notifications.alert import AlertCause, AlertId, AlertState
from autotrading.domain.notifications.alert_page import AlertCursor
from autotrading.domain.notifications.notification import Amount
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
NINE = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
ACCOUNT, FLOW = uuid4(), uuid4()


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


def opened(platform: Platform, user: str, cause: AlertCause, minutes: int = 0) -> AlertId:
    platform.now = NINE + timedelta(minutes=minutes)
    return platform.alerts_of(platform.tenant_of(user)).open(cause)


def alarm() -> AlertCause:
    return AlertCause.reconciliation_alarm(
        ACCOUNT, "test-1", Amount(Decimal(980), "USDC"), Amount(Decimal(1000), "USDC")
    )


def test_the_open_alerts_come_newest_first_by_default(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    alarm_id = opened(platform, "anna", alarm())
    fill_id = opened(platform, "anna", AlertCause.unattributable_fill(ACCOUNT, "test-1", "SOL"), 1)
    resolved = opened(platform, "anna", AlertCause.unattributable_fill(ACCOUNT, "test-1", "ETH"), 2)
    platform.alerts_of(platform.tenant_of("anna")).resolve(resolved)

    response = client.get("/alerts")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [str(fill_id.value), str(alarm_id.value)]
    assert (body["count"], body["next"]) == (2, None)
    assert body["items"][1] == {
        "id": str(alarm_id.value),
        "kind": "reconciliation_alarm",
        "title": "Allarme di riconciliazione",
        "severity": "critical",
        "state": "open",
        "resource": {"kind": "account", "id": str(ACCOUNT), "name": "test-1"},
        "opened_at": "2026-11-18T09:00:00Z",
        "resolved_at": None,
    }


def test_the_list_filters_by_state_severity_resource_and_period(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    paused = opened(platform, "anna", AlertCause.flow_paused(FLOW, "alfa", "credito esaurito"))
    fill = opened(platform, "anna", AlertCause.unattributable_fill(ACCOUNT, "test-1", "SOL"), 10)
    platform.alerts_of(platform.tenant_of("anna")).resolve(fill)

    def ids(**query: str) -> list[str]:
        return [item["id"] for item in client.get("/alerts", params=query).json()["items"]]

    assert ids(state="all") == [str(fill.value), str(paused.value)]
    assert ids(state="resolved") == [str(fill.value)]
    assert ids(state="all", severity="critical") == [str(paused.value)]
    assert ids(state="all", resource_kind="account") == [str(fill.value)]
    assert ids(state="all", resource_id=str(FLOW)) == [str(paused.value)]
    assert ids(state="all", since="2026-11-18T09:05:00Z") == [str(fill.value)]
    assert ids(state="all", until="2026-11-18T09:05:00Z") == [str(paused.value)]


def test_a_full_page_says_where_the_next_starts(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    for minute in range(51):
        opened(platform, "anna", AlertCause.unattributable_fill(ACCOUNT, "test-1", f"A{minute}"), minute)

    first = client.get("/alerts").json()
    rest = client.get("/alerts", params={"cursor": first["next"]}).json()

    assert (len(first["items"]), first["count"]) == (50, 51)
    assert len(rest["items"]) == 1
    assert rest["next"] is None


def test_an_invalid_cursor_is_refused_with_the_reason(client_of: Client) -> None:
    response = client_of("anna").get("/alerts", params={"cursor": "not-a-cursor"})

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "cursore degli avvisi non valido"}


def test_the_cursor_reads_back_as_written() -> None:
    cursor = AlertCursor(NINE, uuid4())

    assert alert_cursor_of(alert_cursor_text(cursor)) == cursor
    with pytest.raises(AlertCursorInvalidError):
        alert_cursor_of(base64.urlsafe_b64encode(b"no-separator").decode())


def test_the_summary_counts_the_open_alerts_of_the_tenant(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    opened(platform, "anna", alarm())
    opened(platform, "anna", AlertCause.flow_paused(FLOW, "alfa", "credito esaurito"))
    client_of("bruno")
    opened(platform, "bruno", AlertCause.flow_paused(uuid4(), "beta", "credito esaurito"))

    assert client.get("/alerts/summary").json() == {"open_count": 2}


def test_the_detail_tells_the_values_and_the_commands_that_resolve_it(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    alert_id = opened(platform, "anna", alarm())

    body = client.get(f"/alerts/{alert_id.value}").json()

    assert body["values"] == [
        {"label": "Saldo letto", "value": "980 USDC"},
        {"label": "Saldo atteso", "value": "1000 USDC"},
    ]
    assert body["commands"] == ["confirm_reconciliation"]


def test_an_alert_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    client_of("bruno")
    theirs = opened(platform, "bruno", AlertCause.unattributable_fill(ACCOUNT, "test-1", "SOL"))

    detail = client.get(f"/alerts/{theirs.value}")
    resolution = client.post(f"/alerts/{theirs.value}/resolution")

    assert (detail.status_code, resolution.status_code) == (404, 404)
    assert reason_of(detail) == {"detail": "avviso non trovato"}


def test_an_alert_without_a_resolution_of_its_own_is_resolved_by_hand(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    alert_id = opened(platform, "anna", AlertCause.unattributable_fill(ACCOUNT, "test-1", "SOL"))

    response = client.post(f"/alerts/{alert_id.value}/resolution")

    assert response.status_code == 204
    assert platform.alerts_of(platform.tenant_of("anna")).get(alert_id).state is AlertState.RESOLVED
    assert client.get(f"/alerts/{alert_id.value}").json()["commands"] == []


def test_an_alert_that_resolves_on_its_own_is_not_resolved_by_hand(client_of: Client, platform: Platform) -> None:
    client = client_of("anna")
    alert_id = opened(platform, "anna", AlertCause.flow_paused(FLOW, "alfa", "credito esaurito"))

    response = client.post(f"/alerts/{alert_id.value}/resolution")

    assert response.status_code == 409
    assert reason_of(response) == {
        "detail": "l'avviso si risolve da solo quando la sua causa sparisce",
        "kind": "flow_paused",
    }
