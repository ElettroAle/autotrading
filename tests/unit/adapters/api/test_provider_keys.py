from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.provider_keys import ProviderKeyRegistrationRequest, ProviderKeyReplacementRequest
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.flows import a_flow
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
KEY = "K-OPENROUTER-TEST"


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


def test_a_registered_key_answers_with_the_provider_only(client_of: Client) -> None:
    response = client_of("anna").post("/provider-keys", json={"provider": "openrouter", "key": KEY})

    assert response.status_code == 201
    assert response.json() == {"provider": "openrouter"}
    assert KEY not in response.text


def test_a_missing_key_answers_with_the_reason(client_of: Client) -> None:
    response = client_of("anna").post("/provider-keys", json={"provider": "openrouter"})

    assert response.status_code == 422
    assert reason_of(response) == {"detail": "chiave obbligatoria"}


def test_a_second_key_for_the_provider_is_a_conflict(client_of: Client) -> None:
    anna = client_of("anna")
    anna.post("/provider-keys", json={"provider": "openrouter", "key": KEY})

    response = anna.post("/provider-keys", json={"provider": "openrouter", "key": KEY + "-new"})

    assert response.status_code == 409
    assert reason_of(response) == {"detail": "chiave già registrata per il fornitore: openrouter"}


def test_the_list_shows_only_the_providers_of_the_user(client_of: Client) -> None:
    client_of("anna").post("/provider-keys", json={"provider": "openrouter", "key": KEY})

    assert client_of("anna").get("/provider-keys").json() == [{"provider": "openrouter"}]
    assert client_of("bruno").get("/provider-keys").json() == []


def test_the_replacement_answers_with_the_provider(client_of: Client) -> None:
    anna = client_of("anna")
    anna.post("/provider-keys", json={"provider": "openrouter", "key": KEY})

    response = anna.put("/provider-keys/openrouter", json={"key": KEY + "-new"})

    assert response.status_code == 200
    assert response.json() == {"provider": "openrouter"}


def test_the_replacement_of_a_key_never_registered_is_not_found(client_of: Client) -> None:
    response = client_of("anna").put("/provider-keys/openrouter", json={"key": KEY})

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "nessuna chiave registrata per il fornitore: openrouter"}


def test_the_removal_answers_with_no_content(client_of: Client) -> None:
    anna = client_of("anna")
    anna.post("/provider-keys", json={"provider": "openrouter", "key": KEY})

    response = anna.delete("/provider-keys/openrouter")

    assert response.status_code == 204
    assert anna.get("/provider-keys").json() == []


def test_the_removal_refused_by_a_flow_is_a_conflict(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    anna.post("/provider-keys", json={"provider": "openrouter", "key": KEY})
    platform.flows.flows.append(a_flow(platform.tenant_of("anna"), status=FlowStatus.ACTIVE))

    response = anna.delete("/provider-keys/openrouter")

    assert response.status_code == 409
    assert reason_of(response) == {"detail": "chiave usata da flussi attivi o in pausa: alfa"}


def test_the_catalog_shows_models_parameters_and_the_providers_with_a_key(client_of: Client) -> None:
    anna = client_of("anna")
    anna.post("/provider-keys", json={"provider": "openrouter", "key": KEY})

    catalog = anna.get("/models").json()

    assert {"name": "openrouter", "key_registered": True} in catalog["providers"]
    assert {"name": "anthropic", "key_registered": False} in catalog["providers"]
    (sonnet,) = [model for model in catalog["models"] if model["name"] == "anthropic/claude-sonnet-5-5"]
    assert sonnet["provider"] == "anthropic"
    assert sonnet["parameters"] == [
        {
            "key": "temperature",
            "label": "temperatura",
            "default": "1",
            "minimum": "0",
            "maximum": "1",
            "whole": False,
            "choices": None,
        },
        {
            "key": "max_tokens",
            "label": "limite di lunghezza della risposta",
            "default": "4096",
            "minimum": "1",
            "maximum": "64000",
            "whole": True,
            "choices": None,
        },
        {
            "key": "reasoning_effort",
            "label": "livello di ragionamento",
            "default": "medio",
            "minimum": None,
            "maximum": None,
            "whole": None,
            "choices": ["basso", "medio", "alto"],
        },
    ]


def test_keys_and_models_need_an_identity(client_of: Client) -> None:
    anonymous = TestClient(client_of("anna").app)

    assert anonymous.get("/provider-keys").status_code == 401
    assert anonymous.get("/models").status_code == 401


def test_the_requests_never_show_the_key() -> None:
    registration = ProviderKeyRegistrationRequest(provider="openrouter", key=KEY)
    replacement = ProviderKeyReplacementRequest(key=KEY)

    assert repr(registration) == "ProviderKeyRegistrationRequest(provider='openrouter')"
    assert KEY not in repr(replacement)
