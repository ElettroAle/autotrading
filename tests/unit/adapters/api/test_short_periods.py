from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.support.flows import a_configuration, a_flow, account_id_of
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]

# ADR periodi-brevi-come-durata-nel-dominio: every reading with a period takes the short periods and refuses the others.
READINGS = (
    "/flows/overview",
    "/flows/ranking",
    "/flows/{flow_id}/state",
    "/flows/{flow_id}/statistics",
    "/flows/{flow_id}/equity",
    "/flows/{flow_id}/forecast-accuracy",
    "/history/cycles",
    "/history/closed-positions",
    "/history/orders",
)


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.now = datetime(2026, 11, 16, 10, 15, tzinfo=UTC)
    return platform


@pytest.fixture
def path_of(platform: Platform) -> Callable[[str], str]:
    configuration = a_configuration(assets=("BTC",), allocated_capital=Decimal(500))
    flow = a_flow(platform.tenant_of("anna"), account_id=account_id_of(platform, "anna"), configuration=configuration)
    platform.flows.flows.append(flow)
    return lambda reading: reading.format(flow_id=flow.id.value)


@pytest.fixture
def anna(platform: Platform) -> TestClient:
    provider = IdentityProvider()
    api = create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(platform.tenants),
        platform.for_tenant,
        provider.authentication(),
    )
    person = platform.directory.person("anna")
    person.roles.add("Utente")
    return TestClient(api, headers={"Authorization": f"Bearer {provider.token_for(person)}"})


@pytest.mark.parametrize("reading", READINGS)
@pytest.mark.parametrize("period", ["30m", "1h", "6h", "12h", "24h"])
def test_every_reading_with_a_period_takes_the_short_periods(
    anna: TestClient, path_of: Callable[[str], str], reading: str, period: str
) -> None:
    response = anna.get(path_of(reading), params={"period": period})

    assert response.status_code == 200


@pytest.mark.parametrize("reading", READINGS)
def test_every_reading_with_a_period_refuses_an_unknown_one_with_the_valid_periods(
    anna: TestClient, path_of: Callable[[str], str], reading: str
) -> None:
    response = anna.get(path_of(reading), params={"period": "2h"})

    assert (response.status_code, reason_of(response)) == (
        400,
        {"detail": "periodo non valido: scegliere tra 30m, 1h, 6h, 12h, 24h, 7d, 30d, all, range"},
    )
