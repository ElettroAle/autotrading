from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, OidcSigningKeys
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.support.identity_provider import SETTINGS, IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]


@pytest.fixture
def client_of() -> Client:
    platform = Platform()
    provider = IdentityProvider()
    verifier = AccessTokenVerifier(SETTINGS, OidcSigningKeys(SETTINGS.discovery_url, provider.fetch))
    api = create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(platform.tenants),
        platform.for_tenant,
        Authentication(SETTINGS, verifier),
    )

    def client(user: str) -> TestClient:
        person = platform.directory.person(user)
        person.roles.add("Utente")
        return TestClient(api, headers={"Authorization": f"Bearer {provider.token_for(person)}"})

    return client


def test_the_catalog_lists_the_sources_with_their_parameters(client_of: Client) -> None:
    response = client_of("anna").get("/sources")

    assert response.status_code == 200
    assert [source["name"] for source in response.json()] == ["indicatori", "pivot", "forecast", "sentiment", "notizie"]


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
