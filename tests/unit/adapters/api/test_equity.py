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
            {"planned_at": "2026-11-10T10:00:00Z", "equity": "312.1"},
            {"planned_at": "2026-11-11T10:00:00Z", "equity": "296.1"},
        ],
    }


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
        params={"period": "range", "from": "2026-11-08T00:00:00Z", "to": "2026-11-09T00:00:00Z"},
    )

    assert [point["planned_at"] for point in response.json()["points"]] == ["2026-11-08T10:00:00Z"]


def test_a_range_without_its_end_is_refused(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")

    response = anna.get(f"/flows/{flow_id}/equity", params={"period": "range", "from": "2026-11-08T00:00:00Z"})

    assert response.status_code == 422
    assert reason_of(response) == {
        "detail": "intervallo dell'equity curve non valido: l'intervallo richiede inizio e fine"
    }


def test_an_unknown_period_is_refused(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")

    assert anna.get(f"/flows/{flow_id}/equity", params={"period": "90d"}).status_code == 422


def test_a_flow_without_cycles_answers_no_point(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = flow_of(platform, "anna")

    assert anna.get(f"/flows/{flow_id}/equity").json()["points"] == []


def test_the_equity_of_a_flow_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    flow_id = flow_of(platform, "bruno")
    record(platform, "bruno", flow_id, 1, "10")

    response = client_of("anna").get(f"/flows/{flow_id}/equity")

    assert response.status_code == 404
    assert client_of("anna").get(f"/flows/{uuid4()}/equity").json()["detail"] == response.json()["detail"]
