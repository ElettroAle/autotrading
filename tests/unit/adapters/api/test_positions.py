from collections.abc import Callable
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, OidcSigningKeys
from autotrading.adapters.inbound.api.errors import ERROR_STATUS
from autotrading.application.orders.errors import (
    NoOpenPositionError,
    OrderAccountNotFoundError,
    OrderExchangeUnavailableError,
    OrderWorkerUnavailableError,
    UnsupportedOrderExchangeError,
)
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.errors import ManualOpeningNotAllowedError
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.trading_access import TradingAccess
from tests.fakes.order_exchange import EXECUTED_AT, REALIZED_ON_CLOSE
from tests.support.identity_provider import SETTINGS, IdentityProvider
from tests.support.platform import HYPERLIQUID, Platform, registration

Client = Callable[[str], TestClient]
LONG_BTC = HeldPosition("BTC", Direction.LONG, Decimal("0.0002"), 2)


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


@pytest.fixture
def credentials(platform: Platform) -> Credentials:
    return platform.accepted_credentials()


@pytest.fixture
def account_id(platform: Platform, client_of: Client, credentials: Credentials) -> str:
    client_of("anna")
    platform.register_account("anna", registration("test-1", HYPERLIQUID, credentials))
    return str(platform.account_named("anna", "test-1").id.value)


def holding(platform: Platform, credentials: Credentials) -> None:
    access = TradingAccess(HYPERLIQUID, credentials.account_address, credentials.secret_key)
    platform.order_exchange.hold(access, LONG_BTC)


def test_a_close_answers_with_what_the_exchange_executed(
    platform: Platform, client_of: Client, account_id: str, credentials: Credentials
) -> None:
    holding(platform, credentials)

    response = client_of("anna").post(f"/accounts/{account_id}/positions/BTC/close")

    (sent,) = platform.order_exchange.sent
    execution = platform.order_exchange.executions[sent.id]
    assert response.status_code == 200
    assert response.json() == {
        "order_id": str(sent.id.value),
        "status": "eseguito",
        "coin": "BTC",
        "filled_size": "0.0002",
        "average_price": str(execution.average_price),
        "fee": str(execution.fee),
        "realized_pnl": str(REALIZED_ON_CLOSE),
        "executed_at": EXECUTED_AT.isoformat(),
        "reason": None,
        "exchange_message": None,
    }


def test_a_refused_close_is_an_outcome_with_reason_and_message(
    platform: Platform, client_of: Client, account_id: str, credentials: Credentials
) -> None:
    holding(platform, credentials)
    platform.order_exchange.rejection = "Insufficient margin to place order. asset=0"

    response = client_of("anna").post(f"/accounts/{account_id}/positions/BTC/close")

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["reason"], body["filled_size"]) == ("rifiutato", "margine insufficiente", None)
    assert body["exchange_message"] == "Insufficient margin to place order. asset=0"


def test_without_a_position_the_close_fails_and_sends_nothing(
    platform: Platform, client_of: Client, account_id: str
) -> None:
    response = client_of("anna").post(f"/accounts/{account_id}/positions/ETH/close")

    assert (response.status_code, response.json()["detail"]) == (409, "nessuna posizione aperta su ETH")
    assert platform.order_exchange.sent == []


def test_another_user_cannot_close_the_position(
    platform: Platform, client_of: Client, account_id: str, credentials: Credentials
) -> None:
    holding(platform, credentials)

    response = client_of("bruno").post(f"/accounts/{account_id}/positions/BTC/close")

    assert (response.status_code, response.json()["detail"]) == (404, "non trovato")
    assert platform.order_exchange.sent == []


def test_an_unreachable_worker_asks_to_retry_the_close(
    platform: Platform, client_of: Client, account_id: str, credentials: Credentials
) -> None:
    holding(platform, credentials)
    platform.worker_reachable = False

    response = client_of("anna").post(f"/accounts/{account_id}/positions/BTC/close")

    assert response.status_code == 503
    assert response.json()["detail"] == "servizio di esecuzione non raggiungibile, riprovare"


def test_a_user_can_never_open_a_position(platform: Platform, client_of: Client, account_id: str) -> None:
    response = client_of("anna").post(f"/accounts/{account_id}/positions", json={"coin": "BTC"})

    assert (response.status_code, response.json()["detail"]) == (403, "apertura manuale non consentita")
    assert platform.order_exchange.sent == []


def test_every_error_of_the_positions_has_a_status() -> None:
    errors = [
        ManualOpeningNotAllowedError,
        NoOpenPositionError,
        OrderAccountNotFoundError,
        UnsupportedOrderExchangeError,
        OrderExchangeUnavailableError,
        OrderWorkerUnavailableError,
    ]

    assert all(error in ERROR_STATUS for error in errors)
