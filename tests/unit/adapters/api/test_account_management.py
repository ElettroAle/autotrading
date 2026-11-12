from collections.abc import Callable
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.accounts import CredentialsReplacementRequest
from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, OidcSigningKeys
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.position import Position, PositionSide
from tests.fakes.exchange import READ_AT, REDACTED_REJECTION
from tests.support.identity_provider import SETTINGS, IdentityProvider
from tests.support.platform import HYPERLIQUID, Platform, registration
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]


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
        Authentication(SETTINGS, verifier, provider.login()),
    )

    def client(user: str) -> TestClient:
        person = platform.directory.person(user)
        person.roles.add("Utente")
        return TestClient(api, headers={"Authorization": f"Bearer {provider.token_for(person)}"})

    return client


@pytest.fixture
def credentials(platform: Platform) -> Credentials:
    return platform.accepted_credentials()


@pytest.fixture
def account_id(platform: Platform, client_of: Client, credentials: Credentials) -> str:
    client_of("anna")
    platform.register_account("anna", registration("test-1", HYPERLIQUID, credentials))
    return str(platform.account_named("anna", "test-1").id.value)


def rotated(platform: Platform, credentials: Credentials, *, accepted: bool = True) -> dict[str, str]:
    new = Credentials(credentials.account_address, "0x" + "cd" * 32)
    if accepted:
        platform.hyperliquid.accept(new)
    return {"account_address": new.account_address, "secret_key": new.secret_key}


def test_the_list_shows_the_accounts_of_the_tenant(client_of: Client, account_id: str) -> None:
    response = client_of("anna").get("/accounts")

    assert response.status_code == 200
    assert response.json() == [{"id": account_id, "name": "test-1", "exchange": HYPERLIQUID, "has_credentials": True}]


def test_the_list_of_another_user_is_empty(client_of: Client, account_id: str) -> None:
    assert account_id
    assert client_of("bruno").get("/accounts").json() == []


def test_the_details_declare_credentials_without_showing_them(
    client_of: Client, account_id: str, credentials: Credentials
) -> None:
    response = client_of("anna").get(f"/accounts/{account_id}")

    assert response.status_code == 200
    assert response.json()["has_credentials"] is True
    assert credentials.account_address not in response.text
    assert credentials.secret_key not in response.text


@pytest.mark.parametrize("whose", ["another tenant", "nobody"])
def test_an_account_of_another_tenant_answers_as_one_that_does_not_exist(
    client_of: Client, account_id: str, whose: str
) -> None:
    target = account_id if whose == "another tenant" else str(uuid4())

    response = client_of("bruno").get(f"/accounts/{target}")

    assert (response.status_code, reason_of(response)) == (404, {"detail": "non trovato"})


def test_accepted_credentials_replace_the_old_ones(
    client_of: Client, platform: Platform, account_id: str, credentials: Credentials
) -> None:
    response = client_of("anna").put(f"/accounts/{account_id}/credentials", json=rotated(platform, credentials))

    assert response.status_code == 200
    assert response.json()["id"] == account_id
    assert not platform.uses_credentials(platform.account_named("anna", "test-1"), credentials)


def test_rejected_credentials_answer_with_the_redacted_message_of_the_exchange(
    client_of: Client, platform: Platform, account_id: str, credentials: Credentials
) -> None:
    body = rotated(platform, credentials, accepted=False)

    response = client_of("anna").put(f"/accounts/{account_id}/credentials", json=body)

    assert response.status_code == 422
    assert reason_of(response) == {
        "detail": "credenziali rifiutate dall'exchange",
        "exchange_message": REDACTED_REJECTION,
    }
    assert body["account_address"] not in response.text.lower()


def test_credentials_of_another_exchange_account_are_refused(
    client_of: Client, platform: Platform, account_id: str
) -> None:
    other = platform.accepted_credentials()
    body = {"account_address": other.account_address, "secret_key": other.secret_key}

    response = client_of("anna").put(f"/accounts/{account_id}/credentials", json=body)

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "le credenziali appartengono a un altro conto dell'exchange"},
    )


def test_another_user_cannot_replace_the_credentials(
    client_of: Client, platform: Platform, account_id: str, credentials: Credentials
) -> None:
    response = client_of("bruno").put(f"/accounts/{account_id}/credentials", json=rotated(platform, credentials))

    assert (response.status_code, reason_of(response)) == (404, {"detail": "non trovato"})
    assert platform.uses_credentials(platform.account_named("anna", "test-1"), credentials)


def test_the_replacement_request_never_shows_the_credentials() -> None:
    request = CredentialsReplacementRequest.model_validate({"account_address": "0xaddr", "secret_key": "0xsk"})

    shown = repr(request)

    assert "0xaddr" not in shown
    assert "0xsk" not in shown


def test_the_state_of_an_account_is_read_from_the_exchange(
    client_of: Client, platform: Platform, account_id: str, credentials: Credentials
) -> None:
    btc = Position("BTC", PositionSide.LONG, Decimal("0.01"), 2, Decimal(60000), Decimal("5.5"), None)
    platform.hyperliquid.open_position(credentials, btc)

    response = client_of("anna").get(f"/accounts/{account_id}/state")

    assert response.status_code == 200
    assert response.json() == {
        "balance": {"amount": "1000.00", "currency": "USDC"},
        "available_margin": {"amount": "1000.00", "currency": "USDC"},
        "positions": [
            {
                "coin": "BTC",
                "side": "long",
                "size": "0.01",
                "leverage": 2,
                "entry_price": "60000",
                "unrealized_pnl": "5.5",
                "liquidation_price": None,
            }
        ],
        "read_at": READ_AT.isoformat(),
    }


def test_another_user_cannot_read_the_state(client_of: Client, account_id: str) -> None:
    response = client_of("bruno").get(f"/accounts/{account_id}/state")

    assert (response.status_code, reason_of(response)) == (404, {"detail": "non trovato"})


def test_an_unreachable_exchange_asks_to_retry_the_reading(
    client_of: Client, platform: Platform, account_id: str
) -> None:
    platform.hyperliquid.reachable = False

    response = client_of("anna").get(f"/accounts/{account_id}/state")

    assert (response.status_code, reason_of(response)) == (503, {"detail": "exchange non raggiungibile, riprovare"})


def test_an_unreachable_worker_asks_to_retry_the_reading(
    client_of: Client, platform: Platform, account_id: str
) -> None:
    platform.worker_reachable = False

    response = client_of("anna").get(f"/accounts/{account_id}/state")

    assert (response.status_code, reason_of(response)) == (
        503,
        {"detail": "servizio di esecuzione non raggiungibile, riprovare"},
    )


def test_credentials_that_do_not_open_are_a_fault_of_the_installation(
    client_of: Client, platform: Platform, account_id: str
) -> None:
    platform.vault.clear()

    response = client_of("anna").get(f"/accounts/{account_id}/state")

    assert (response.status_code, reason_of(response)) == (500, {"detail": "credenziali del conto non leggibili"})


def test_an_account_without_positions_is_removed_and_no_longer_listed(
    client_of: Client, platform: Platform, account_id: str
) -> None:
    response = client_of("anna").delete(f"/accounts/{account_id}")

    assert (response.status_code, response.content) == (204, b"")
    assert client_of("anna").get("/accounts").json() == []
    assert client_of("anna").get(f"/accounts/{account_id}").status_code == 404
    assert [str(removed.id.value) for removed in platform.accounts.removed] == [account_id]


def test_an_account_with_open_positions_is_kept_without_confirmation(
    client_of: Client, platform: Platform, account_id: str, credentials: Credentials
) -> None:
    btc = Position("BTC", PositionSide.LONG, Decimal("0.01"), 2, Decimal(60000), Decimal("5.5"), None)
    platform.hyperliquid.open_position(credentials, btc)

    response = client_of("anna").delete(f"/accounts/{account_id}", params={"confirmed": "false"})

    assert (response.status_code, reason_of(response)) == (
        409,
        {"detail": "il conto ha posizioni aperte che resteranno sull'exchange senza gestione"},
    )
    assert platform.accounts.removed == []


def test_a_confirmed_removal_keeps_the_positions_and_removes_the_account(
    client_of: Client, platform: Platform, account_id: str, credentials: Credentials
) -> None:
    btc = Position("BTC", PositionSide.LONG, Decimal("0.01"), 2, Decimal(60000), Decimal("5.5"), None)
    platform.hyperliquid.open_position(credentials, btc)
    platform.worker_reachable = False

    response = client_of("anna").delete(f"/accounts/{account_id}", params={"confirmed": "true"})

    assert response.status_code == 204
    assert platform.hyperliquid.read_state(credentials).positions == (btc,)


def test_another_user_cannot_remove_the_account(client_of: Client, platform: Platform, account_id: str) -> None:
    response = client_of("bruno").delete(f"/accounts/{account_id}", params={"confirmed": "true"})

    assert (response.status_code, reason_of(response)) == (404, {"detail": "non trovato"})
    assert platform.accounts.removed == []


def test_a_removed_name_can_be_registered_again(client_of: Client, account_id: str, credentials: Credentials) -> None:
    client_of("anna").delete(f"/accounts/{account_id}")

    response = client_of("anna").post(
        "/accounts",
        json={
            "name": "test-1",
            "exchange": HYPERLIQUID,
            "account_address": credentials.account_address,
            "secret_key": credentials.secret_key,
        },
    )

    assert response.status_code == 201
