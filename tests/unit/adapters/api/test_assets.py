from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import HYPERLIQUID, Platform
from tests.support.problems import reason_of

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


def test_lists_the_assets_tradable_on_the_exchange_of_the_installation_by_name(
    platform: Platform, client_of: Client
) -> None:
    platform.markets[HYPERLIQUID].assets = frozenset({"SOL", "BTC", "ETH"})

    response = client_of("anna").get("/assets")

    assert (response.status_code, response.json()) == (200, ["BTC", "ETH", "SOL"])


def test_an_exchange_out_of_reach_answers_service_unavailable(platform: Platform, client_of: Client) -> None:
    platform.markets[HYPERLIQUID].reachable = False

    response = client_of("anna").get("/assets")

    assert (response.status_code, reason_of(response)) == (503, {"detail": "exchange non raggiungibile, riprovare"})


def test_the_assets_need_an_identity(client_of: Client) -> None:
    assert TestClient(client_of("anna").app).get("/assets").status_code == 401
