from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from tests.fakes.equity_snapshots import InMemoryEquitySnapshotRepositoryAdapter
from tests.support.flows import a_configuration, a_flow
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]


@pytest.fixture
def platform() -> Platform:
    world = Platform()
    world.now = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
    return world


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


def flow_of(platform: Platform, user: str) -> UUID:
    configuration = replace(a_configuration(), allocated_capital=Decimal("300.50"))
    flow = a_flow(platform.tenant_of(user), configuration=configuration)
    platform.flows.flows.append(flow)
    return flow.id.value


def record(platform: Platform, user: str, flow_id: UUID, days_ago: int, realized_pnl: str) -> None:
    snapshot = EquitySnapshot(
        flow_id,
        platform.now - timedelta(days=days_ago),
        Decimal(300),
        Decimal(realized_pnl),
        Decimal("3.10"),
        Decimal(1),
        Decimal(0),
    )
    InMemoryEquitySnapshotRepositoryAdapter(platform.equity_snapshots, platform.tenant_of(user)).record(snapshot)


def test_the_equity_curve_answers_a_point_per_cycle_with_the_initial_capital(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    record(platform, "anna", flow_id, 2, "10")
    record(platform, "anna", flow_id, 1, "-6")

    response = anna.get(f"/flows/{flow_id}/equity")

    assert response.status_code == 200
    assert response.json() == {
        "initial_capital": "300.5",
        "points": [
            {"planned_at": "2026-11-10T10:00:00Z", "equity": "312.1", "change_percent": "0.00"},
            {"planned_at": "2026-11-11T10:00:00Z", "equity": "296.1", "change_percent": "-5.13"},
        ],
    }


def test_the_change_starts_from_the_first_point_of_the_period(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    record(platform, "anna", flow_id, 40, "-100")
    record(platform, "anna", flow_id, 20, "6.9")
    record(platform, "anna", flow_id, 10, "37.8")

    response = anna.get(f"/flows/{flow_id}/equity", params={"period": "30d"})

    assert [point["change_percent"] for point in response.json()["points"]] == ["0.00", "10.00"]


def test_the_change_is_null_when_the_first_point_has_no_equity(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    record(platform, "anna", flow_id, 2, "-302.1")
    record(platform, "anna", flow_id, 1, "0")

    response = anna.get(f"/flows/{flow_id}/equity")

    assert [point["change_percent"] for point in response.json()["points"]] == [None, None]


def test_no_change_reads_zero_even_from_a_negative_equity(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    record(platform, "anna", flow_id, 2, "-312.1")
    record(platform, "anna", flow_id, 1, "-312.1")

    response = anna.get(f"/flows/{flow_id}/equity")

    assert [point["change_percent"] for point in response.json()["points"]] == ["0.00", "0.00"]


def test_the_last_7_days_leave_the_older_cycles_out(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    record(platform, "anna", flow_id, 8, "10")
    record(platform, "anna", flow_id, 6, "-6")

    response = anna.get(f"/flows/{flow_id}/equity", params={"period": "7d"})

    assert [point["planned_at"] for point in response.json()["points"]] == ["2026-11-06T10:00:00Z"]


def test_a_range_reads_from_its_start_to_its_end(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")
    for days in (5, 4, 3):
        record(platform, "anna", flow_id, days, str(days))

    response = anna.get(
        f"/flows/{flow_id}/equity",
        params={"period": "range", "from": "2026-11-08", "to": "2026-11-08"},
    )

    assert [point["planned_at"] for point in response.json()["points"]] == ["2026-11-08T10:00:00Z"]


def test_a_range_without_its_end_is_refused(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")

    response = anna.get(f"/flows/{flow_id}/equity", params={"period": "range", "from": "2026-11-08"})

    assert response.status_code == 400
    assert reason_of(response) == {
        "detail": "periodo non valido: un intervallo ha il giorno iniziale e il giorno finale"
    }


def test_an_unknown_period_is_refused(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")

    assert anna.get(f"/flows/{flow_id}/equity", params={"period": "90d"}).status_code == 400


def test_a_flow_without_cycles_answers_no_point(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")

    assert anna.get(f"/flows/{flow_id}/equity").json()["points"] == []


def test_a_draft_answers_no_initial_capital_and_no_point(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    draft = anna.post(f"/flows/{flow_of(platform, 'anna')}/duplicate").json()

    assert anna.get(f"/flows/{draft['id']}/equity").json() == {"initial_capital": None, "points": []}


def test_the_equity_of_a_flow_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    flow_id = flow_of(platform, "bruno")
    record(platform, "bruno", flow_id, 1, "10")

    response = client_of("anna").get(f"/flows/{flow_id}/equity")

    assert response.status_code == 404
    assert client_of("anna").get(f"/flows/{uuid4()}/equity").json()["detail"] == response.json()["detail"]
