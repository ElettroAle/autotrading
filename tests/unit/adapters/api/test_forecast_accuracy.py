"""The route of the mean error of the forecasts of a flow (R3.6.1, ADR errore-medio-della-previsione-nell-api)."""

from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.flow import Flow
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from tests.support.flows import a_flow
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

ONE_HOUR = ForecastHorizon(60)

Client = Callable[[str], TestClient]


@pytest.fixture
def platform() -> Platform:
    return Platform()


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


def flow_of(platform: Platform, user: str) -> Flow:
    flow = a_flow(platform.tenant_of(user))
    platform.flows.flows.append(flow)
    return flow


def forecast(
    platform: Platform,
    flow: Flow,
    *,
    predicted: str,
    actual: str | None,
    age: timedelta,
    horizon: ForecastHorizon = ONE_HOUR,
) -> None:
    made_at = platform.now - age - horizon.length
    price = None if actual is None else Decimal(actual)
    recorded = PriceForecast(
        flow.id.value, "BTC", horizon, made_at, Decimal(60000), Decimal(predicted), 7, False, price
    )
    platform.forecasts_of(flow.tenant_id).add(recorded)


def test_the_error_of_each_asset_and_horizon_answers_with_amounts_as_text(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    forecast(platform, flow, predicted="60500", actual="60000", age=timedelta(hours=1))
    forecast(platform, flow, predicted="61000", actual="61400", age=timedelta(hours=2))
    forecast(platform, flow, predicted="60000", actual=None, age=timedelta(hours=3))
    forecast(platform, flow, predicted="60100.50", actual="60000", age=timedelta(hours=1), horizon=ForecastHorizon(15))

    response = anna.get(f"/flows/{flow.id.value}/forecast-accuracy")

    assert response.status_code == 200
    assert response.json() == {
        "forecasts": [
            {
                "asset": "BTC",
                "horizon_minutes": 15,
                "mean_absolute_error": "100.5",
                "mean_percent_error": "0.17",
                "evaluated": 1,
                "unevaluable": 0,
            },
            {
                "asset": "BTC",
                "horizon_minutes": 60,
                "mean_absolute_error": "450",
                "mean_percent_error": "0.74",
                "evaluated": 2,
                "unevaluable": 1,
            },
        ]
    }


def test_the_mean_percent_error_keeps_two_decimals(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    forecast(platform, flow, predicted="60600", actual="60000", age=timedelta(hours=1))

    (entry,) = anna.get(f"/flows/{flow.id.value}/forecast-accuracy").json()["forecasts"]

    assert entry["mean_percent_error"] == "1.00"


def test_without_evaluated_forecasts_in_the_period_the_means_are_null(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    forecast(platform, flow, predicted="60500", actual="60000", age=timedelta(days=10))

    (entry,) = anna.get(f"/flows/{flow.id.value}/forecast-accuracy", params={"period": "7d"}).json()["forecasts"]

    assert (entry["mean_absolute_error"], entry["mean_percent_error"], entry["evaluated"]) == (None, None, 0)


def test_a_range_takes_its_minutes_from_from_and_to(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    forecast(platform, flow, predicted="60900", actual="60000", age=timedelta(days=10))
    forecast(platform, flow, predicted="60300", actual="60000", age=timedelta(days=2))
    expiry = platform.now - timedelta(days=2)
    start, end = (expiry - timedelta(minutes=1)).isoformat(), expiry.isoformat()

    params = {"period": "range", "from": start, "to": end}
    (entry,) = anna.get(f"/flows/{flow.id.value}/forecast-accuracy", params=params).json()["forecasts"]

    assert (entry["mean_absolute_error"], entry["evaluated"]) == ("300", 1)


def test_a_flow_without_forecasts_answers_no_error(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")

    assert anna.get(f"/flows/{flow.id.value}/forecast-accuracy").json() == {"forecasts": []}


def test_an_invalid_period_answers_400_with_the_reason(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")

    params = {"period": "range", "from": "2026-11-03T10:00", "to": "2026-11-01T10:00"}
    response = anna.get(f"/flows/{flow.id.value}/forecast-accuracy", params=params)

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "periodo non valido: l'inizio è successivo alla fine"}


def test_the_error_of_a_flow_of_another_user_does_not_exist(client_of: Client, platform: Platform) -> None:
    flow = flow_of(platform, "bruno")

    response = client_of("anna").get(f"/flows/{flow.id.value}/forecast-accuracy")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "flusso non trovato"}
