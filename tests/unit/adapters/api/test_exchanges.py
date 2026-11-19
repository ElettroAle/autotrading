"""The exchanges an account can be registered on, with their network (Bug 277)."""

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

    assert (response.status_code, [exchange["name"] for exchange in response.json()]) == (200, ["Bybit", HYPERLIQUID])


def test_lists_each_exchange_with_the_network_its_adapter_is_configured_on(
    platform: Platform, client_of: Client
) -> None:
    platform.exchanges[HYPERLIQUID] = FakeExchangeAdapter(real=True)

    response = client_of("anna").get("/exchanges")

    assert (response.status_code, [(exchange["name"], exchange["network"]) for exchange in response.json()]) == (
        200,
        [(HYPERLIQUID, "real")],
    )


def test_an_exchange_on_the_test_network_is_listed_as_test(client_of: Client) -> None:
    assert [exchange["network"] for exchange in client_of("anna").get("/exchanges").json()] == ["test"]


def test_lists_each_exchange_with_the_fields_its_credentials_need(client_of: Client) -> None:
    """R2.3.9: the dashboard builds the registration from these fields, secrets shown hidden."""
    [exchange] = client_of("anna").get("/exchanges").json()

    assert exchange["fields"] == [
        {"name": "account_address", "label": "Indirizzo del conto", "secret": False},
        {"name": "secret_key", "label": "Chiave dell'API wallet", "secret": True},
    ]


def test_the_exchanges_need_an_identity(client_of: Client) -> None:
    assert TestClient(client_of("anna").app).get("/exchanges").status_code == 401


def test_the_exchanges_are_described_among_the_routes_of_the_accounts(client_of: Client) -> None:
    operation = client_of("anna").get("/openapi.json").json()["paths"]["/exchanges"]["get"]

    assert operation["tags"] == ["conti"]


def test_lists_each_exchange_with_the_name_its_adapter_gives_the_network(platform: Platform, client_of: Client) -> None:
    """R2.3.10: the dashboard names the network without knowing any exchange."""
    platform.exchanges[HYPERLIQUID] = FakeExchangeAdapter(network_name="sandbox")

    [exchange] = client_of("anna").get("/exchanges").json()

    assert (exchange["network"], exchange["network_name"]) == ("test", "sandbox")


def test_lists_whether_the_user_gives_the_expiry_of_the_credentials(platform: Platform, client_of: Client) -> None:
    """R6.2.2: the dashboard shows the field of the expiry only where the exchange does not read it."""
    assert [exchange["expiry_editable"] for exchange in client_of("anna").get("/exchanges").json()] == [True]
    platform.hyperliquid.reads_expiry = True

    assert [exchange["expiry_editable"] for exchange in client_of("anna").get("/exchanges").json()] == [False]
