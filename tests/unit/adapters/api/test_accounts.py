from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.accounts import AccountRegistrationRequest
from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, OidcSigningKeys
from autotrading.adapters.inbound.api.errors import ERROR_STATUS
from autotrading.application.accounts.errors import (
    AccountNameInUseError,
    ExchangeRejectedCredentialsError,
    ExchangeUnavailableError,
    UnsupportedExchangeError,
)
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.accounts.errors import AccountNameRequiredError, CredentialsRequiredError, ExchangeRequiredError
from tests.fakes.exchange import REDACTED_REJECTION
from tests.support.identity_provider import SETTINGS, IdentityProvider
from tests.support.platform import HYPERLIQUID, Platform


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def client(platform: Platform) -> TestClient:
    provider = IdentityProvider()
    verifier = AccessTokenVerifier(SETTINGS, OidcSigningKeys(SETTINGS.discovery_url, provider.fetch))
    api = create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(platform.tenants),
        platform.for_tenant,
        Authentication(SETTINGS, verifier),
    )
    anna = platform.directory.person("anna")
    anna.roles.add("Utente")
    token = provider.token_for(anna)
    return TestClient(api, headers={"Authorization": f"Bearer {token}"})


def register(client: TestClient, **body: Any) -> httpx.Response:
    response: httpx.Response = client.post("/accounts", json=body)
    return response


def accepted_body(platform: Platform, name: str = "test-1") -> dict[str, str]:
    credentials = platform.accepted_credentials()
    return {
        "name": name,
        "exchange": HYPERLIQUID,
        "account_address": credentials.account_address,
        "secret_key": credentials.secret_key,
    }


def test_registers_the_account_and_reports_the_balance(client: TestClient, platform: Platform) -> None:
    response = register(client, **accepted_body(platform))

    saved = platform.accounts_of("anna")
    assert response.status_code == 201
    assert response.json() == {
        "id": str(saved[0].id.value),
        "name": "test-1",
        "exchange": HYPERLIQUID,
        "balance": {"amount": "1000.00", "currency": "USDC"},
    }


def test_the_answer_never_carries_the_credentials(client: TestClient, platform: Platform) -> None:
    body = accepted_body(platform)

    text = register(client, **body).text

    assert body["secret_key"] not in text
    assert body["account_address"] not in text


def test_rejected_credentials_report_the_reason_and_the_exchange_message(
    client: TestClient, platform: Platform
) -> None:
    body = accepted_body(platform) | {"secret_key": "0x" + "ee" * 32}

    response = register(client, **body)

    assert response.status_code == 422
    assert response.json() == {"detail": "credenziali rifiutate dall'exchange", "exchange_message": REDACTED_REJECTION}


def test_an_unsupported_exchange_lists_the_supported_ones(client: TestClient, platform: Platform) -> None:
    response = register(client, **accepted_body(platform) | {"exchange": "Binance"})

    assert (response.status_code, response.json()) == (
        422,
        {"detail": "exchange non supportato", "supported": [HYPERLIQUID]},
    )


def test_a_name_in_use_is_a_conflict(client: TestClient, platform: Platform) -> None:
    register(client, **accepted_body(platform))

    response = register(client, **accepted_body(platform))

    assert (response.status_code, response.json()) == (409, {"detail": "nome del conto già in uso"})


def test_an_unreachable_exchange_asks_to_retry(client: TestClient, platform: Platform) -> None:
    body = accepted_body(platform)
    platform.hyperliquid.reachable = False

    response = register(client, **body)

    assert (response.status_code, response.json()) == (503, {"detail": "exchange non raggiungibile, riprovare"})


@pytest.mark.parametrize(
    ("missing", "reason"),
    [("name", "nome obbligatorio"), ("exchange", "exchange obbligatorio"), ("secret_key", "credenziali obbligatorio")],
)
def test_missing_data_is_named(client: TestClient, platform: Platform, missing: str, reason: str) -> None:
    body = accepted_body(platform)
    del body[missing]

    response = register(client, **body)

    assert (response.status_code, response.json()) == (422, {"detail": reason})


def test_a_malformed_request_never_echoes_what_was_sent(client: TestClient) -> None:
    secret = "0x" + "ab" * 32

    response = register(client, name="test-1", exchange=HYPERLIQUID, account_address="0x1", secret_key={"k": secret})

    assert response.status_code == 422
    assert secret not in response.text
    assert response.json()["detail"][0]["loc"] == ["body", "secret_key"]


def test_every_error_of_the_registration_has_a_status() -> None:
    errors = [
        AccountNameRequiredError,
        ExchangeRequiredError,
        CredentialsRequiredError,
        UnsupportedExchangeError,
        AccountNameInUseError,
        ExchangeRejectedCredentialsError,
        ExchangeUnavailableError,
    ]

    assert all(error in ERROR_STATUS for error in errors)


def test_the_request_representation_never_shows_the_credentials() -> None:
    body = {"name": "test-1", "exchange": HYPERLIQUID, "account_address": "0xaddr", "secret_key": "0xsk"}

    shown = repr(AccountRegistrationRequest(**body))

    assert "0xaddr" not in shown
    assert "0xsk" not in shown
