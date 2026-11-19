from collections.abc import Callable
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.fakes.sources import FakeNewsAdapter, FakeSentimentAdapter
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


def test_a_trial_answers_the_values_the_adapter_read_with_their_instant_and_the_time_of_the_answer(
    client_of: Client,
) -> None:
    response = client_of("anna").post(
        "/sources/indicatori/adapters/Hyperliquid/trials", json={"asset": "BTC", "parameters": {"lunghezza_serie": 5}}
    )

    body = response.json()
    assert (response.status_code, body["outcome"], body["reason"], body["permanent"]) == (200, "succeeded", None, False)
    assert [value["values"]["prezzo"] for value in body["values"]] == ["100"]
    assert body["data_at"] == body["values"][0]["reference_at"]
    assert body["response_milliseconds"] >= 0


def test_a_source_that_fails_is_the_outcome_of_the_trial_not_an_error(platform: Platform) -> None:
    platform.source_systems = replace(platform.source_systems, news=FakeNewsAdapter(reachable=False))

    response = client_of_platform(platform)("anna").post("/sources/notizie/adapters/RSS/trials", json={})

    assert response.status_code == 200
    assert {name: response.json()[name] for name in ("outcome", "values", "data_at", "reason", "permanent")} == {
        "outcome": "failed",
        "values": [],
        "data_at": None,
        "reason": "fonte non raggiungibile: notizie",
        "permanent": False,
    }


def test_a_parameter_outside_its_values_stops_the_trial_and_names_the_field_and_its_limits(client_of: Client) -> None:
    response = client_of("anna").post(
        "/sources/indicatori/adapters/Hyperliquid/trials", json={"asset": "BTC", "parameters": {"lunghezza_serie": 51}}
    )

    assert (response.status_code, reason_of(response)) == (
        422,
        {
            "detail": "parametro fuori dai valori ammessi: lunghezza serie, da 1 a 50",
            "field": "lunghezza_serie",
            "minimum": 1,
            "maximum": 50,
        },
    )


def test_a_trial_of_a_per_asset_source_without_an_asset_does_not_start(client_of: Client) -> None:
    response = client_of("anna").post("/sources/pivot/adapters/Hyperliquid/trials", json={})

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "scegli l'asset su cui provare la fonte pivot", "field": "asset"},
    )


@pytest.mark.parametrize(
    ("path", "detail"),
    [
        ("/sources/oroscopo/adapters/RSS/trials", "fonte non disponibile: oroscopo"),
        ("/sources/notizie/adapters/Altro/trials", "adapter non disponibile per la fonte notizie: Altro"),
    ],
)
def test_a_trial_of_a_source_or_an_adapter_outside_the_catalog_is_not_found(
    client_of: Client, path: str, detail: str
) -> None:
    response = client_of("anna").post(path, json={})

    assert (response.status_code, reason_of(response)) == (404, {"detail": detail})


def test_a_trial_with_the_worker_away_is_a_service_not_available(platform: Platform) -> None:
    platform.worker_reachable = False

    response = client_of_platform(platform)("anna").post("/sources/notizie/adapters/RSS/trials", json={})

    assert (response.status_code, reason_of(response)) == (
        503,
        {"detail": "servizio di esecuzione non raggiungibile, riprovare"},
    )


def test_the_trial_needs_an_identity(client_of: Client) -> None:
    assert TestClient(client_of("anna").app).post("/sources/notizie/adapters/RSS/trials", json={}).status_code == 401
