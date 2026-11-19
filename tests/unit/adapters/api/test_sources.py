from collections.abc import Callable
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.fakes.sources import FakeSentimentAdapter
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of
from tests.support.source_keys import API_KEY

Client = Callable[[str], TestClient]


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def client_of(platform: Platform) -> Client:
    return client_of_platform(platform)


def client_of_platform(platform: Platform) -> Client:
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


def offer_paid_sentiment(platform: Platform) -> None:
    """A paid adapter of the sentiment beside those of the platform, which asks for a secret API key (R4.1.2)."""
    systems = platform.source_systems
    paid = FakeSentimentAdapter("LunarCrush", configuration_fields=(API_KEY,))
    platform.source_systems = replace(systems, sentiments=(*systems.sentiments, paid))


def test_the_catalog_lists_the_sources_with_the_adapters_that_offer_them(client_of: Client) -> None:
    response = client_of("anna").get("/sources")

    assert response.status_code == 200
    assert [(source["name"], [adapter["name"] for adapter in source["adapters"]]) for source in response.json()] == [
        ("indicatori", ["Hyperliquid"]),
        ("pivot", ["Hyperliquid"]),
        ("forecast", ["Prophet"]),
        ("sentiment", ["alternative.me", "CoinMarketCap"]),
        ("notizie", ["RSS"]),
    ]


def test_every_adapter_shows_its_parameters_its_configuration_and_its_history(client_of: Client) -> None:
    body = client_of("anna").get("/sources/notizie").json()

    assert body["adapters"] == [
        {
            "name": "RSS",
            "description": "feed delle testate",
            "parameters": body["parameters"],
            "configuration_fields": [],
            "offers_history": False,
            "configured": None,
            "unavailable_reason": None,
        }
    ]


def test_one_source_shows_description_scope_and_parameters(client_of: Client) -> None:
    response = client_of("anna").get("/sources/notizie")

    body = response.json()
    assert (response.status_code, body["name"], body["per_asset"]) == (200, "notizie", False)
    assert body["description"]
    assert body["parameters"] == [
        {"key": "numero_notizie", "label": "numero notizie", "default": 10, "minimum": 1, "maximum": 50},
        {"key": "eta_massima_ore", "label": "età massima ore", "default": 24, "minimum": 1, "maximum": 168},
    ]


def test_a_source_outside_the_catalog_is_not_found(client_of: Client) -> None:
    response = client_of("anna").get("/sources/oroscopo")

    assert (response.status_code, reason_of(response)) == (404, {"detail": "fonte non disponibile: oroscopo"})


def test_the_catalog_needs_an_identity(client_of: Client) -> None:
    assert TestClient(client_of("anna").app).get("/sources").status_code == 401


def test_an_adapter_the_tenant_did_not_configure_says_why_it_is_not_activatable(platform: Platform) -> None:
    """R4.1.2: it stays in the list of the flow, with the reason."""
    offer_paid_sentiment(platform)

    adapters = client_of_platform(platform)("anna").get("/sources/sentiment").json()["adapters"]

    assert [(adapter["name"], adapter["configured"], adapter["unavailable_reason"]) for adapter in adapters] == [
        ("alternative.me", None, None),
        ("CoinMarketCap", None, None),
        ("LunarCrush", False, "configura l'adapter LunarCrush in Impostazioni \u203a Chiavi"),
    ]


def test_an_adapter_the_tenant_configured_is_activatable(platform: Platform) -> None:
    offer_paid_sentiment(platform)
    anna = client_of_platform(platform)("anna")
    anna.put("/source-credentials/LunarCrush", json={"values": {"api_key": "K-LUNAR"}})

    [sentiment] = [source for source in anna.get("/sources").json() if source["name"] == "sentiment"]

    assert [(adapter["configured"], adapter["unavailable_reason"]) for adapter in sentiment["adapters"]][-1] == (
        True,
        None,
    )
