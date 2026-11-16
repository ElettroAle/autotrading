"""The address of the notifications by email from the programmatic interface (R3.5.2, ADR
canale-email-delle-notifiche-con-smtp).
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
WITHOUT_ADDRESS = {"address": None, "warning": None}


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


def test_an_indicated_address_reads_back_for_its_tenant_only(client_of: Client) -> None:
    anna = client_of("anna")

    response = anna.put("/notifications/email", json={"address": " anna@example.com "})

    assert response.status_code == 204
    assert anna.get("/notifications/email").json() == {"address": "anna@example.com", "warning": None}
    assert client_of("bruno").get("/notifications/email").json() == WITHOUT_ADDRESS


@pytest.mark.parametrize("address", ["anna", "anna@", "@example.com"])
def test_an_address_without_the_form_of_an_email_is_refused(client_of: Client, address: str) -> None:
    response = client_of("anna").put("/notifications/email", json={"address": address})

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "indirizzo email non valido"}


def test_a_removed_address_answers_with_no_content_and_is_no_more(client_of: Client) -> None:
    anna = client_of("anna")
    anna.put("/notifications/email", json={"address": "anna@example.com"})

    response = anna.delete("/notifications/email")

    assert response.status_code == 204
    assert anna.get("/notifications/email").json() == WITHOUT_ADDRESS


def test_without_a_mail_service_the_settings_carry_the_warning(platform: Platform, client_of: Client) -> None:
    platform.mail_service.configured = False

    body = client_of("anna").get("/notifications/email").json()

    assert body == {"address": None, "warning": "le email non partono: servizio di posta non configurato"}


def test_a_test_email_is_accepted_and_reaches_the_address(platform: Platform, client_of: Client) -> None:
    anna = client_of("anna")
    anna.put("/notifications/email", json={"address": "anna@example.com"})

    response = anna.post("/notifications/email/test")

    assert response.status_code == 202
    [email] = platform.mailer.received_by("anna@example.com")
    assert email.subject == "AutoTrading: prova delle notifiche"


def test_a_test_email_without_an_address_is_a_conflict(client_of: Client) -> None:
    response = client_of("anna").post("/notifications/email/test")

    assert response.status_code == 409
    assert reason_of(response) == {"detail": "nessun indirizzo email per le notifiche"}


def test_a_test_email_without_a_mail_service_is_a_conflict(platform: Platform, client_of: Client) -> None:
    platform.mail_service.configured = False

    response = client_of("anna").post("/notifications/email/test")

    assert response.status_code == 409
    assert reason_of(response) == {"detail": "servizio di posta non configurato"}


def test_the_email_functions_need_a_login(platform: Platform) -> None:
    anonymous = TestClient(
        create_api(HealthReport("1.0.0", "dev"), ResolveTenantUseCase(platform.tenants), platform.for_tenant, None)
    )

    assert anonymous.get("/notifications/email").status_code == 401
    assert anonymous.put("/notifications/email", json={"address": "anna@example.com"}).status_code == 401
    assert anonymous.delete("/notifications/email").status_code == 401
    assert anonymous.post("/notifications/email/test").status_code == 401
