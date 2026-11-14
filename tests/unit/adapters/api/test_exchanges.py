from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.fakes.exchange import FakeExchangeAdapter
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import HYPERLIQUID, Platform

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


def test_lists_the_exchanges_the_registration_of_an_account_accepts_by_name(
    platform: Platform, client_of: Client
) -> None:
    platform.exchanges["Bybit"] = FakeExchangeAdapter()

    response = client_of("anna").get("/exchanges")

    assert (response.status_code, response.json()) == (200, ["Bybit", HYPERLIQUID])


def test_the_exchanges_need_an_identity(client_of: Client) -> None:
    assert TestClient(client_of("anna").app).get("/exchanges").status_code == 401


def test_the_exchanges_are_described_among_the_routes_of_the_accounts(client_of: Client) -> None:
    operation = client_of("anna").get("/openapi.json").json()["paths"]["/exchanges"]["get"]

    assert operation["tags"] == ["conti"]
