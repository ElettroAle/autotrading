import base64
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.history import cursor_of, cursor_text
from autotrading.application.flows.errors import HistoryCursorInvalidError
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.history import HistoryCursor
from autotrading.domain.flows.statistics_period import TimeWindow
from tests.fakes.flow_history import HistoryStore
from tests.support.history import ACCOUNT, FLOW, a_cycle_row, a_position_row, an_order_row
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
FIRST = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.now = datetime(2026, 11, 30, 23, 0, tzinfo=UTC)
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


def history_of(platform: Platform, user: str) -> HistoryStore:
    return platform.history_of(platform.tenant_of(user)).store


def test_gives_the_cycles_of_a_version_of_a_flow_with_flow_and_version(platform: Platform, client_of: Client) -> None:
    history_of(platform, "anna").cycles.extend(
        a_cycle_row(FIRST + timedelta(days=day), version=1 if day < 14 else 2) for day in range(30)
    )

    response = client_of("anna").get("/history/cycles", params={"flow_id": str(FLOW), "version": 2})

    assert response.status_code == 200
    body = response.json()
    assert len(body["cycles"]) == 16
    assert body["cycles"][0] | {"decisions": None} == {
        "flow_id": str(FLOW),
        "flow": "alfa",
        "version": 2,
        "planned_at": "2026-11-30T12:00:00Z",
        "started_at": "2026-11-30T12:00:00Z",
        "outcome": "concluso",
        "failure": None,
        "decisions": None,
    }
    assert body["cycles"][-1]["planned_at"] == "2026-11-15T12:00:00Z"
    assert body["next"] is None


def test_rejects_a_version_without_a_flow(client_of: Client) -> None:
    response = client_of("anna").get("/history/cycles", params={"version": 2})

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "la versione richiede un flusso"}


def test_rejects_a_version_below_one(client_of: Client) -> None:
    response = client_of("anna").get("/history/cycles", params={"flow_id": str(FLOW), "version": 0})

    assert response.status_code == 422


def test_rejects_a_period_the_platform_does_not_know(client_of: Client) -> None:
    response = client_of("anna").get("/history/orders", params={"period": "1y"})

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "periodo non valido: scegliere tra all, 7d, 30d, range"}


def test_rejects_a_page_the_platform_did_not_give(client_of: Client) -> None:
    response = client_of("anna").get("/history/closed-positions", params={"after": "non-un-cursore"})

    assert response.status_code == 422
    assert reason_of(response) == {"detail": "pagina dello storico non valida"}


def test_reads_the_period_of_a_range_of_days(platform: Platform, client_of: Client) -> None:
    store = history_of(platform, "anna")
    store.closed_positions.extend(
        a_position_row(FIRST + timedelta(days=day), asset=asset) for day in range(30) for asset in ("BTC", "ETH")
    )

    response = client_of("anna").get(
        "/history/closed-positions",
        params={"asset": "ETH", "period": "range", "from": "2026-11-10", "to": "2026-11-20"},
    )

    positions = response.json()["positions"]
    assert {position["asset"] for position in positions} == {"ETH"}
    assert [position["closed_at"][:10] for position in positions][::10] == ["2026-11-20", "2026-11-10"]
    assert len(positions) == 11


def test_gives_a_closed_position_with_its_flow_and_its_result(platform: Platform, client_of: Client) -> None:
    row = a_position_row(FIRST)
    history_of(platform, "anna").closed_positions.append(row)

    position = client_of("anna").get("/history/closed-positions").json()["positions"][0]

    assert position == {
        "id": str(row.entry.position_id),
        "flow_id": str(FLOW),
        "flow": "alfa",
        "asset": "ETH",
        "side": "long",
        "leverage": 2,
        "margin": "100",
        "open_price": "3000",
        "close_price": "3150",
        "opened_at": "2026-11-01T10:00:00Z",
        "closed_at": "2026-11-01T12:00:00Z",
        "duration_seconds": 7200,
        "pnl": "10",
        "pnl_percent_of_margin": "10",
        "fees": "0.42",
        "reason": "decisione dell'agente",
        "opening_cycle": None,
        "closing_cycle": None,
    }


def test_gives_each_order_with_price_quantity_and_fee_of_its_executions(platform: Platform, client_of: Client) -> None:
    row = an_order_row(FIRST)
    history_of(platform, "anna").orders.append(row)

    response = client_of("anna").get("/history/orders", params={"account_id": str(ACCOUNT)})

    order = response.json()["orders"][0]
    assert order == {
        "id": str(row.entry.order_id),
        "created_at": "2026-11-01T12:00:00Z",
        "account_id": str(ACCOUNT),
        "account": "principale",
        "flow_id": str(FLOW),
        "flow": "alfa",
        "asset": "BTC",
        "direction": "long",
        "closing": False,
        "leverage": 3,
        "requested_size": "0.02",
        "status": "eseguito",
        "origin": "flusso",
        "executions": [
            {"executed_at": "2026-11-01T12:00:01Z", "price": "91000.5", "size": "0.015", "fee": "0.41"},
            {"executed_at": "2026-11-01T12:00:02Z", "price": "91001", "size": "0.005", "fee": "0.14"},
        ],
    }


def test_the_next_page_starts_after_the_last_order_of_the_previous(platform: Platform, client_of: Client) -> None:
    history_of(platform, "anna").orders.extend(an_order_row(FIRST + timedelta(minutes=minute)) for minute in range(55))
    client = client_of("anna")

    first = client.get("/history/orders").json()
    second = client.get("/history/orders", params={"after": first["next"]}).json()

    assert len(first["orders"]) == 50
    assert len(second["orders"]) == 5
    assert second["next"] is None
    assert second["orders"][0]["created_at"] == "2026-11-01T12:04:00Z"


def test_a_filter_reaches_the_history_with_the_window_read_now(platform: Platform, client_of: Client) -> None:
    history = platform.history_of(platform.tenant_of("anna"))

    client_of("anna").get("/history/cycles", params={"period": "7d", "asset": "BTC", "account_id": str(ACCOUNT)})

    query = history.queries[-1]
    assert (query.criteria.asset, query.criteria.account_id, query.criteria.flow_id) == ("BTC", ACCOUNT, None)
    assert query.window == TimeWindow(since=platform.now - timedelta(days=7))


def test_a_user_reads_only_the_history_of_their_tenant(platform: Platform, client_of: Client) -> None:
    history_of(platform, "anna").closed_positions.append(a_position_row(FIRST, asset="BTC"))
    history_of(platform, "bruno")

    response = client_of("bruno").get("/history/closed-positions", params={"asset": "BTC"})

    assert response.json() == {"positions": [], "next": None}


def test_a_cursor_survives_its_text() -> None:
    cursor = HistoryCursor(FIRST, UUID("00000000-0000-4000-8000-000000000042"))

    assert cursor_of(cursor_text(cursor)) == cursor


@pytest.mark.parametrize("text", ["!!", base64.urlsafe_b64encode(b"2026-11-01|non-un-uuid").decode(), "e30="])
def test_rejects_a_cursor_the_platform_did_not_write(text: str) -> None:
    with pytest.raises(HistoryCursorInvalidError):
        cursor_of(text)
