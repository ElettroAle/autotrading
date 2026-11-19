"""The section Fonti of the page of the keys over HTTP: the adapters that need configuration, their fields and state,
never a secret (R4.1.2, ADR credenziali-degli-adapter-delle-fonti)."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.source_credentials import SourceCredentialsRequest
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.fakes.sources import FakeSentimentAdapter
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of
from tests.support.source_keys import ACCOUNT, API_KEY

Client = Callable[[str], TestClient]
TYPED_KEY = "K-LUNAR-TEST"
SAVED_AT = datetime(2026, 11, 14, 9, 0, tzinfo=UTC)
TODAY = datetime(2026, 11, 20, 6, 0, tzinfo=UTC)
VALUES = {"api_key": TYPED_KEY, "account": "anna"}


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.now = TODAY
    systems = platform.source_systems
    paid = FakeSentimentAdapter("LunarCrush", configuration_fields=(API_KEY, ACCOUNT))
    platform.source_systems = replace(systems, sentiments=(*systems.sentiments, paid))
    return platform


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


def test_the_section_lists_only_the_adapters_that_need_configuration_with_their_fields(client_of: Client) -> None:
    response = client_of("anna").get("/source-credentials")

    assert response.status_code == 200
    assert response.json() == [
        {
            "adapter": "LunarCrush",
            "sources": ["sentiment"],
            "configuration_fields": [
                {"name": "api_key", "label": "Chiave API", "secret": True},
                {"name": "account", "label": "Account", "secret": False},
            ],
            "configured": False,
            "public_values": {},
            "registered_at": None,
            "rejected": False,
            "expiry": None,
            "expiry_status": "unknown",
            "days_left": None,
            "expiry_editable": True,
        }
    ]


def test_configured_credentials_answer_the_public_values_and_never_the_secret(client_of: Client) -> None:
    anna = client_of("anna")

    saved = anna.put("/source-credentials/LunarCrush", json={"values": VALUES, "expires_on": "2026-12-15"})
    response = anna.get("/source-credentials")

    assert saved.status_code == 204
    [summary] = response.json()
    assert (summary["configured"], summary["public_values"], summary["registered_at"]) == (
        True,
        {"account": "anna"},
        SAVED_AT.isoformat(),
    )
    assert (summary["expiry"], summary["expiry_status"], summary["days_left"]) == (
        {"expires_on": "2026-12-15", "source": "entered"},
        "expiring",
        25,
    )
    assert TYPED_KEY not in response.text


def test_a_missing_secret_answers_with_the_field(client_of: Client) -> None:
    response = client_of("anna").put("/source-credentials/LunarCrush", json={"values": {"account": "anna"}})

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "chiave API obbligatorio", "field": "api_key"},
    )


def test_an_adapter_without_configuration_refuses_credentials(client_of: Client) -> None:
    response = client_of("anna").put("/source-credentials/alternative.me", json={"values": {}})

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "l'adapter alternative.me non richiede configurazione"},
    )


def test_an_unknown_adapter_is_not_found(client_of: Client) -> None:
    response = client_of("anna").put("/source-credentials/Oroscopo", json={"values": VALUES})

    assert (response.status_code, reason_of(response)) == (
        404,
        {"detail": "adapter della fonte non disponibile: Oroscopo"},
    )


def test_the_expiry_is_given_and_forgotten(client_of: Client) -> None:
    anna = client_of("anna")
    anna.put("/source-credentials/LunarCrush", json={"values": VALUES})

    given = anna.put("/source-credentials/LunarCrush/expiry", json={"expires_on": "2026-11-21"})
    expiring = anna.get("/source-credentials").json()[0]
    forgotten = anna.put("/source-credentials/LunarCrush/expiry", json={})

    assert (given.status_code, forgotten.status_code) == (204, 204)
    assert (expiring["expiry_status"], expiring["days_left"]) == ("expiring", 1)
    assert anna.get("/source-credentials").json()[0]["expiry"] is None


def test_the_expiry_of_credentials_never_given_is_not_found(client_of: Client) -> None:
    response = client_of("anna").put("/source-credentials/LunarCrush/expiry", json={"expires_on": "2026-12-15"})

    assert (response.status_code, reason_of(response)) == (
        404,
        {"detail": "credenziali dell'adapter non trovate: LunarCrush"},
    )


def test_removed_credentials_leave_the_adapter_not_configured(client_of: Client) -> None:
    anna = client_of("anna")
    anna.put("/source-credentials/LunarCrush", json={"values": VALUES})

    removed = anna.delete("/source-credentials/LunarCrush")

    assert removed.status_code == 204
    assert anna.get("/source-credentials").json()[0]["configured"] is False
    assert anna.delete("/source-credentials/LunarCrush").status_code == 404


def test_the_credentials_of_a_tenant_are_not_seen_by_another(client_of: Client) -> None:
    client_of("bruno").put("/source-credentials/LunarCrush", json={"values": VALUES})

    assert client_of("anna").get("/source-credentials").json()[0]["configured"] is False


def test_the_request_never_shows_the_values_it_carries() -> None:
    request = SourceCredentialsRequest(values=VALUES)

    assert TYPED_KEY not in repr(request)
    assert TYPED_KEY not in str(request)


def test_the_section_needs_an_identity(client_of: Client) -> None:
    assert TestClient(client_of("anna").app).get("/source-credentials").status_code == 401
