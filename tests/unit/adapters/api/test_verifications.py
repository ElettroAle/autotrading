from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, OidcSigningKeys
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.trading_access import TradingAccess
from tests.support.identity_provider import SETTINGS, IdentityProvider
from tests.support.platform import HYPERLIQUID, STARTED_AT, Platform, registration

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


def test_a_run_answers_with_the_outcome_of_each_step(platform: Platform, client_of: Client, account_id: str) -> None:
    response = client_of("anna").post(f"/accounts/{account_id}/verifications")

    body = response.json()
    (run,) = platform.runs_of(platform.tenant_of("anna")).runs
    assert response.status_code == 200
    assert (body["id"], body["account_id"], body["user_id"]) == (str(run.id), account_id, run.user_id)
    assert (body["environment"], body["started_at"], body["outcome"]) == ("dev", STARTED_AT.isoformat(), "superata")
    assert (body["total_fee"], body["realized_pnl"], body["warning"]) == (str(run.total_fee), "1.75", None)
    assert [step["step"] for step in body["steps"]] == [step.step.value for step in run.steps]


def test_the_steps_carry_what_was_read_and_what_the_orders_did(client_of: Client, account_id: str) -> None:
    opening, after_opening, _, after_closing = (
        client_of("anna").post(f"/accounts/{account_id}/verifications").json()["steps"]
    )

    assert opening["reading"] is None
    assert opening["order"]["succeeded"]
    assert opening["order"]["realized_pnl"] == "0"
    assert after_opening["order"] is None
    assert after_opening["reading"]["positions"] == [{"coin": "BTC", "side": "long", "size": "0.00010", "leverage": 2}]
    assert (after_opening["reading"]["balance"], after_opening["reading"]["currency"]) == ("1000.00", "USDC")
    assert after_closing["reading"]["positions"] == []


def test_a_failed_run_is_still_the_answer(platform: Platform, client_of: Client, account_id: str) -> None:
    platform.order_exchange.closing_rejection = "Order could not immediately match against any resting orders."

    response = client_of("anna").post(f"/accounts/{account_id}/verifications")

    assert response.status_code == 200
    body = response.json()
    assert (body["outcome"], body["warning"]) == (
        "fallita al passo chiusura",
        "sul conto resta aperta una posizione long su BTC",
    )
    assert body["steps"][-1]["order"]["message"] == "Order could not immediately match against any resting orders."


def test_an_account_with_btc_open_does_not_start(
    platform: Platform, client_of: Client, account_id: str, credentials: Credentials
) -> None:
    access = TradingAccess(HYPERLIQUID, credentials.account_address, credentials.secret_key)
    platform.order_exchange.hold(access, HeldPosition("BTC", Direction.SHORT, Decimal("0.001"), 4))

    response = client_of("anna").post(f"/accounts/{account_id}/verifications")

    assert (response.status_code, response.json()["detail"]) == (409, "posizione già aperta su BTC")
    assert platform.order_exchange.sent == []


def test_another_user_cannot_run_the_procedure_on_the_account(
    platform: Platform, client_of: Client, account_id: str
) -> None:
    response = client_of("bruno").post(f"/accounts/{account_id}/verifications")

    assert (response.status_code, response.json()["detail"]) == (404, "non trovato")
    assert platform.order_exchange.sent == []


def test_an_exchange_that_cannot_be_read_before_starting_asks_to_retry(
    platform: Platform, client_of: Client, account_id: str
) -> None:
    platform.hyperliquid.reachable = False

    response = client_of("anna").post(f"/accounts/{account_id}/verifications")

    assert response.status_code == 503
    assert platform.order_exchange.sent == []


def test_an_unreachable_worker_asks_to_retry_the_procedure(
    platform: Platform, client_of: Client, account_id: str
) -> None:
    platform.worker_reachable = False

    response = client_of("anna").post(f"/accounts/{account_id}/verifications")

    assert (response.status_code, response.json()["detail"]) == (
        503,
        "servizio di esecuzione non raggiungibile, riprovare",
    )


def test_the_chosen_amount_is_the_value_of_the_opening(platform: Platform, client_of: Client, account_id: str) -> None:
    response = client_of("anna").post(f"/accounts/{account_id}/verifications", json={"amount": "25"})

    assert response.status_code == 200
    opening = platform.order_exchange.sent[0]
    assert opening.size * platform.order_exchange.markets["BTC"].mid_price == Decimal(25)


@pytest.mark.parametrize("amount", ["0", "-5", "dieci"])
def test_an_amount_that_is_not_a_positive_number_is_refused_before_the_worker(
    platform: Platform, client_of: Client, account_id: str, amount: str
) -> None:
    response = client_of("anna").post(f"/accounts/{account_id}/verifications", json={"amount": amount})

    assert response.status_code == 422
    assert platform.runs_of(platform.tenant_of("anna")).runs == []
    assert platform.order_exchange.sent == []


def test_a_procedure_already_in_progress_on_the_account_does_not_start_another(
    platform: Platform, client_of: Client, account_id: str
) -> None:
    platform.running_verifications.add((UUID(account_id), "BTC"))

    response = client_of("anna").post(f"/accounts/{account_id}/verifications")

    assert (response.status_code, response.json()["detail"]) == (409, "procedura di verifica già in corso su BTC")
    assert platform.order_exchange.sent == []
