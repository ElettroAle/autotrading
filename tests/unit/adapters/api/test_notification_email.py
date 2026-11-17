"""The address of the notifications by email and its test from the programmatic interface (R3.5.2, R3.5.5, ADR
invio-dal-server-di-posta-del-tenant).
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.notifications.notification import Notification
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
SERVER_MISSING = "le email non partono: server di posta non configurato"
WITHOUT_ADDRESS = {"address": None, "warning": SERVER_MISSING}


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


def configure_server(platform: Platform, user: str) -> None:
    platform.mail_servers.configure(platform.tenant_of(user), f"{user}@example.com")


def ready(platform: Platform, client: TestClient, user: str) -> None:
    configure_server(platform, user)
    client.put("/notifications/email", json={"address": f"{user}@example.com"})


def test_an_indicated_address_reads_back_for_its_tenant_only(platform: Platform, client_of: Client) -> None:
    anna = client_of("anna")
    configure_server(platform, "anna")

    response = anna.put("/notifications/email", json={"address": " anna@example.com "})

    assert response.status_code == 204
    assert anna.get("/notifications/email").json() == {"address": "anna@example.com", "warning": None}
    assert client_of("bruno").get("/notifications/email").json() == WITHOUT_ADDRESS


@pytest.mark.parametrize("address", ["anna", "anna@", "@example.com"])
def test_an_address_without_the_form_of_an_email_is_refused(client_of: Client, address: str) -> None:
    response = client_of("anna").put("/notifications/email", json={"address": address})

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "indirizzo email non valido", "address": address}


def test_a_removed_address_answers_with_no_content_and_is_no_more(client_of: Client) -> None:
    anna = client_of("anna")
    anna.put("/notifications/email", json={"address": "anna@example.com"})

    response = anna.delete("/notifications/email")

    assert response.status_code == 204
    assert anna.get("/notifications/email").json() == WITHOUT_ADDRESS


def test_without_a_mail_server_the_settings_carry_the_warning(client_of: Client) -> None:
    body = client_of("anna").get("/notifications/email").json()

    assert body == WITHOUT_ADDRESS


def test_a_test_email_leaves_at_once_from_the_server_of_the_user(platform: Platform, client_of: Client) -> None:
    anna = client_of("anna")
    ready(platform, anna, "anna")

    response = anna.post("/notifications/email/test")

    assert response.status_code == 204
    [email] = platform.mailer.received_by("anna@example.com")
    assert email.subject == Notification.test().title
    assert [login.host for login in platform.mailer.sent_from("anna@example.com")] == ["smtp.example.com"]


def test_a_test_email_without_an_address_is_a_conflict(platform: Platform, client_of: Client) -> None:
    anna = client_of("anna")
    configure_server(platform, "anna")

    response = anna.post("/notifications/email/test")

    assert response.status_code == 409
    assert reason_of(response) == {"detail": "nessun indirizzo email per le notifiche"}


def test_a_test_email_without_a_mail_server_is_a_conflict(client_of: Client) -> None:
    anna = client_of("anna")
    anna.put("/notifications/email", json={"address": "anna@example.com"})

    response = anna.post("/notifications/email/test")

    assert response.status_code == 409
    assert reason_of(response) == {"detail": "server di posta non configurato"}


def test_a_login_refused_by_the_server_answers_with_its_reason(platform: Platform, client_of: Client) -> None:
    anna = client_of("anna")
    ready(platform, anna, "anna")
    platform.mailer.refusing_login = True

    response = anna.post("/notifications/email/test")

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "il server di posta ha rifiutato l'accesso: controlla utente e password"}


def test_an_email_the_server_does_not_take_is_unavailable(platform: Platform, client_of: Client) -> None:
    anna = client_of("anna")
    ready(platform, anna, "anna")
    platform.mailer.accepting = False

    response = anna.post("/notifications/email/test")

    assert response.status_code == 503
    assert reason_of(response) == {"detail": "email non consegnata"}


def test_the_email_functions_need_a_login(platform: Platform) -> None:
    anonymous = TestClient(
        create_api(HealthReport("1.0.0", "dev"), ResolveTenantUseCase(platform.tenants), platform.for_tenant, None)
    )

    assert anonymous.get("/notifications/email").status_code == 401
    assert anonymous.put("/notifications/email", json={"address": "anna@example.com"}).status_code == 401
    assert anonymous.delete("/notifications/email").status_code == 401
    assert anonymous.post("/notifications/email/test").status_code == 401
