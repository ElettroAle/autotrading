from collections.abc import Callable
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, OidcSigningKeys
from autotrading.application.notifications.link_chat import LinkChatCommand
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.link_code import ALPHABET
from tests.support.identity_provider import SETTINGS, IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
CHAT = ChatId(1001)


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def client_of(platform: Platform) -> Client:
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


def test_a_requested_code_answers_with_the_code_and_its_expiry(platform: Platform, client_of: Client) -> None:
    response = client_of("anna").post("/telegram/link-code")

    assert response.status_code == 201
    body = response.json()
    assert len(body["code"]) == 8
    assert set(body["code"]) <= set(ALPHABET)
    assert body["expires_at"] == (platform.now + timedelta(minutes=15)).isoformat().replace("+00:00", "Z")


def test_the_chat_reads_as_linked_once_the_bot_received_the_code(platform: Platform, client_of: Client) -> None:
    anna = client_of("anna")
    assert anna.get("/telegram/chat").json() == {"linked": False}

    platform.link_chat().execute(LinkChatCommand(CHAT, anna.post("/telegram/link-code").json()["code"]))

    assert anna.get("/telegram/chat").json() == {"linked": True}
    assert client_of("bruno").get("/telegram/chat").json() == {"linked": False}


def test_unlinking_answers_with_no_content(platform: Platform, client_of: Client) -> None:
    anna = client_of("anna")
    platform.link_chat().execute(LinkChatCommand(CHAT, anna.post("/telegram/link-code").json()["code"]))

    response = anna.delete("/telegram/chat")

    assert response.status_code == 204
    assert anna.get("/telegram/chat").json() == {"linked": False}


def test_unlinking_without_a_chat_is_not_found(client_of: Client) -> None:
    response = client_of("anna").delete("/telegram/chat")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "nessuna chat Telegram collegata"}


def test_the_telegram_functions_need_a_login(platform: Platform, client_of: Client) -> None:
    client_of("anna")
    anonymous = TestClient(
        create_api(HealthReport("1.0.0", "dev"), ResolveTenantUseCase(platform.tenants), platform.for_tenant, None)
    )

    assert anonymous.post("/telegram/link-code").status_code == 401
