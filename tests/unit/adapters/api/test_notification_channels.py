"""The channels of the types of event and the exceptions of the flows from the programmatic interface (R3.5.3, ADR
canali-delle-notifiche-per-tipo-di-evento, ADR canali-delle-notifiche-come-insieme).
"""

from collections.abc import Callable
from urllib.parse import quote
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.flows import a_flow
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
OPENING = "apertura di una posizione"
ALARM = "allarme di riconciliazione"


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


def flow_of(platform: Platform, user: str, name: str, status: FlowStatus = FlowStatus.STOPPED) -> Flow:
    flow = a_flow(platform.tenant_of(user), name=name, status=status)
    platform.flows.flows.append(flow)
    return flow


def exception_path(flow: Flow, event: str) -> str:
    return f"/notifications/channels/flows/{flow.id.value}/{quote(event)}"


def test_a_user_who_never_chose_reads_every_type_of_event_on_its_default_channel(
    platform: Platform, client_of: Client
) -> None:
    alfa = flow_of(platform, "anna", "alfa")
    flow_of(platform, "anna", "vecchio", FlowStatus.ARCHIVED)

    body = client_of("anna").get("/notifications/channels").json()

    assert body["events"][0] == {
        "event": OPENING,
        "channels": ["Telegram"],
        "of_flow": True,
        "warnings": ["Telegram non collegato"],
    }
    reduced = next(each for each in body["events"] if each["event"] == "decisione ridotta dal rischio")
    assert reduced == {"event": "decisione ridotta dal rischio", "channels": [], "of_flow": True, "warnings": []}
    assert body["flows"] == [{"flow_id": str(alfa.id.value), "name": "alfa", "exceptions": []}]
    assert body["warnings"] == ["Telegram non collegato", "email non indicata", "server di posta non configurato"]
    assert body["channels"] == [
        {"channel": "Telegram", "configured": False, "warnings": ["Telegram non collegato"]},
        {
            "channel": "email",
            "configured": False,
            "warnings": ["email non indicata", "server di posta non configurato"],
        },
    ]


def test_the_channels_warn_of_the_missing_mail_server_whatever_the_choices(
    platform: Platform, client_of: Client
) -> None:
    anna = client_of("anna")
    platform.mail_servers.configure(platform.tenant_of("anna"), "anna@example.com")
    anna.put("/notifications/email", json={"address": "anna@example.com"})
    before = anna.get("/notifications/channels").json()["warnings"]
    platform.mail_servers.store.clear()

    after = anna.get("/notifications/channels").json()["warnings"]

    assert before == ["Telegram non collegato"]
    assert after == ["Telegram non collegato", "server di posta non configurato"]


def test_a_chosen_channel_reads_back_for_its_tenant_only(client_of: Client) -> None:
    anna = client_of("anna")

    response = anna.put("/notifications/channels", json={"event": "ciclo fallito", "channels": ["email", "Telegram"]})

    assert response.status_code == 204
    chosen = next(
        each for each in anna.get("/notifications/channels").json()["events"] if each["event"] == "ciclo fallito"
    )
    assert chosen["channels"] == ["Telegram", "email"]
    bruno = client_of("bruno").get("/notifications/channels").json()["events"]
    assert next(each for each in bruno if each["event"] == "ciclo fallito")["channels"] == ["Telegram"]


def test_no_channel_chosen_silences_the_event(client_of: Client) -> None:
    anna = client_of("anna")

    response = anna.put("/notifications/channels", json={"event": "ciclo fallito", "channels": []})

    assert response.status_code == 204
    events = anna.get("/notifications/channels").json()["events"]
    assert next(each for each in events if each["event"] == "ciclo fallito")["channels"] == []


def test_an_unknown_channel_or_event_is_an_invalid_request(client_of: Client) -> None:
    anna = client_of("anna")

    for body in (
        {"event": "ciclo fallito", "channels": ["sms"]},
        {"event": "ciclo fallito", "channels": ["entrambi"]},
        {"event": "ciclo fallito", "channel": "email"},
        {"event": "eclissi", "channels": ["email"]},
    ):
        assert anna.put("/notifications/channels", json=body).status_code == 422, body


def test_an_exception_of_a_flow_reads_back_and_is_removed(platform: Platform, client_of: Client) -> None:
    alfa = flow_of(platform, "anna", "alfa")
    anna = client_of("anna")

    put = anna.put(exception_path(alfa, OPENING), json={"channels": ["email"]})
    excepted = anna.get("/notifications/channels").json()["flows"][0]["exceptions"]
    removed = anna.delete(exception_path(alfa, OPENING))

    assert put.status_code == 204
    assert excepted == [
        {
            "event": OPENING,
            "channels": ["email"],
            "of_flow": True,
            "warnings": ["email non indicata", "server di posta non configurato"],
        }
    ]
    assert removed.status_code == 204
    assert anna.get("/notifications/channels").json()["flows"][0]["exceptions"] == []


def test_an_exception_for_an_event_of_the_account_is_refused(platform: Platform, client_of: Client) -> None:
    alfa = flow_of(platform, "anna", "alfa")

    response = client_of("anna").put(exception_path(alfa, ALARM), json={"channels": ["email"]})

    assert response.status_code == 400
    assert reason_of(response) == {
        "detail": "allarme di riconciliazione è un evento del conto: segue la scelta generale",
        "event": ALARM,
    }


def test_an_exception_for_a_flow_of_another_tenant_is_not_found(platform: Platform, client_of: Client) -> None:
    alfa = flow_of(platform, "anna", "alfa")

    response = client_of("bruno").put(exception_path(alfa, OPENING), json={"channels": ["email"]})
    unknown = client_of("anna").put(
        f"/notifications/channels/flows/{uuid4()}/{quote(OPENING)}", json={"channels": ["email"]}
    )

    assert response.status_code == unknown.status_code == 404
    assert reason_of(response) == reason_of(unknown) == {"detail": "flusso non trovato"}
