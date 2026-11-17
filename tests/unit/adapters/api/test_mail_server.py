"""The mail server of the user from the programmatic interface: its password never comes back (R3.5.5, ADR
server-di-posta-per-tenant).
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
PASSWORD = "password-per-le-app"  # noqa: S105 - the password of a fake mail server
SERVER = {
    "host": "smtp.example.com",
    "port": 587,
    "security": "STARTTLS",
    "username": "anna@example.com",
    "password": PASSWORD,
}
SAVED = {
    "host": "smtp.example.com",
    "port": 587,
    "security": "STARTTLS",
    "username": "anna@example.com",
    "sender": "anna@example.com",
    "password_saved": True,
}


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


def test_a_saved_server_reads_back_without_its_password_for_its_tenant_only(client_of: Client) -> None:
    anna = client_of("anna")

    response = anna.put("/notifications/mail-server", json=SERVER)

    assert response.status_code == 204
    read = anna.get("/notifications/mail-server")
    assert read.json() == SAVED
    assert PASSWORD not in read.text
    assert client_of("bruno").get("/notifications/mail-server").json() is None


def test_a_change_without_the_password_keeps_the_saved_one(platform: Platform, client_of: Client) -> None:
    anna = client_of("anna")
    anna.put("/notifications/mail-server", json=SERVER)
    change = {key: value for key, value in SERVER.items() if key != "password"} | {"port": 465, "security": "TLS"}

    response = anna.put("/notifications/mail-server", json=change)

    assert response.status_code == 204
    assert anna.get("/notifications/mail-server").json() == SAVED | {"port": 465, "security": "TLS"}
    tenant = platform.tenant_of("anna")
    assert platform.mail_servers.opener(tenant).open(platform.mail_servers.store[tenant].password) == PASSWORD


def test_a_first_server_without_a_password_is_refused(client_of: Client) -> None:
    response = client_of("anna").put("/notifications/mail-server", json=SERVER | {"password": None})

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "password del server di posta mancante"}


def test_a_port_out_of_range_is_refused_with_the_value(client_of: Client) -> None:
    response = client_of("anna").put("/notifications/mail-server", json=SERVER | {"port": 70000})

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "porta del server di posta non valida: da 1 a 65535", "port": 70000}


def test_a_security_other_than_starttls_or_tls_is_not_valid(client_of: Client) -> None:
    response = client_of("anna").put("/notifications/mail-server", json=SERVER | {"security": "SSL"})

    assert response.status_code == 422
    assert PASSWORD not in response.text


def test_a_removed_server_answers_with_no_content_and_is_no_more(client_of: Client) -> None:
    anna = client_of("anna")
    anna.put("/notifications/mail-server", json=SERVER)

    response = anna.delete("/notifications/mail-server")

    assert response.status_code == 204
    assert anna.get("/notifications/mail-server").json() is None


def test_the_mail_server_needs_a_login(platform: Platform) -> None:
    anonymous = TestClient(
        create_api(HealthReport("1.0.0", "dev"), ResolveTenantUseCase(platform.tenants), platform.for_tenant, None)
    )

    assert anonymous.get("/notifications/mail-server").status_code == 401
    assert anonymous.put("/notifications/mail-server", json=SERVER).status_code == 401
    assert anonymous.delete("/notifications/mail-server").status_code == 401
