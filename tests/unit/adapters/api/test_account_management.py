from collections.abc import Callable
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.accounts import CredentialsReplacementRequest
from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.key_expiry import KeyExpiry
from autotrading.domain.accounts.position import Position, PositionSide
from tests.fakes.exchange import READ_AT, REDACTED_REJECTION
from tests.support.credentials import hyperliquid_credentials
from tests.support.flows import a_configuration, a_flow
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import HYPERLIQUID, Platform, registration
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]


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


@pytest.fixture
def credentials(platform: Platform) -> Credentials:
    return platform.accepted_credentials()


@pytest.fixture
def account_id(platform: Platform, client_of: Client, credentials: Credentials) -> str:
    client_of("anna")
    platform.register_account("anna", registration("test-1", HYPERLIQUID, credentials))
    return str(platform.account_named("anna", "test-1").id.value)


def rotated(platform: Platform, credentials: Credentials, *, accepted: bool = True) -> dict[str, dict[str, str]]:
    """What the dashboard sends: only the secret field, the account address stays the one kept (Bug 401)."""
    new = hyperliquid_credentials(credentials.value("account_address"), "0x" + "cd" * 32)
    if accepted:
        platform.hyperliquid.accept(new)
    return {"credentials": {"secret_key": new.value("secret_key")}}


def test_the_list_shows_the_accounts_of_the_tenant(
    client_of: Client, account_id: str, credentials: Credentials
) -> None:
    response = client_of("anna").get("/accounts")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": account_id,
            "name": "test-1",
            "exchange": HYPERLIQUID,
            "has_credentials": True,
            "network": "test",
            "network_name": "testnet",
            "allocated_capital": "0",
            "currency": "USDC",
            "public_fields": {"account_address": credentials.value("account_address")},
            "expiry": None,
            "expiry_status": "unknown",
            "days_left": None,
            "expiry_editable": True,
            "max_direction_exposure_percent": None,
            "reconciliation_interval_minutes": 5,
        }
    ]


def test_the_list_carries_the_capital_the_flows_of_the_account_hold(
    client_of: Client, platform: Platform, account_id: str
) -> None:
    platform.flows.flows += [
        a_flow(
            platform.tenant_of("anna"),
            name=name,
            account_id=UUID(account_id),
            configuration=a_configuration(allocated_capital=capital),
        )
        for name, capital in (("alfa", Decimal("300.50")), ("beta", Decimal("199.50")))
    ]

    [listed] = client_of("anna").get("/accounts").json()
    details = client_of("anna").get(f"/accounts/{account_id}").json()

    assert (listed["allocated_capital"], listed["currency"]) == ("500", "USDC")
    assert (details["network"], details["network_name"], details["allocated_capital"], details["currency"]) == (
        "test",
        "testnet",
        "500",
        "USDC",
    )


def test_the_list_of_another_user_is_empty(client_of: Client, account_id: str) -> None:
    assert account_id
    assert client_of("bruno").get("/accounts").json() == []


def test_the_details_show_the_public_fields_and_only_declare_the_secret_ones(
    client_of: Client, account_id: str, credentials: Credentials
) -> None:
    response = client_of("anna").get(f"/accounts/{account_id}")

    assert response.status_code == 200
    assert response.json()["has_credentials"] is True
    assert response.json()["public_fields"] == {"account_address": credentials.value("account_address")}
    assert credentials.value("secret_key") not in response.text


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
    assert body["credentials"]["secret_key"] not in response.text.lower()


def test_a_public_field_sent_in_a_replacement_is_refused_by_its_label(
    client_of: Client, platform: Platform, account_id: str
) -> None:
    other = platform.accepted_credentials()
    body = {"credentials": dict(other.values)}

    response = client_of("anna").put(f"/accounts/{account_id}/credentials", json=body)

    assert (response.status_code, reason_of(response)) == (
        400,
        {
            "detail": "indirizzo del conto non si sostituisce: per cambiarlo rimuovi il conto e registrane uno nuovo",
            "field": "account_address",
        },
    )


def test_another_user_cannot_replace_the_credentials(
    client_of: Client, platform: Platform, account_id: str, credentials: Credentials
) -> None:
    response = client_of("bruno").put(f"/accounts/{account_id}/credentials", json=rotated(platform, credentials))

    assert (response.status_code, reason_of(response)) == (404, {"detail": "non trovato"})
    assert platform.uses_credentials(platform.account_named("anna", "test-1"), credentials)


def test_the_replacement_request_never_shows_the_credentials() -> None:
    request = CredentialsReplacementRequest.model_validate(
        {"credentials": {"account_address": "0xaddr", "secret_key": "0xsk"}}
    )

    shown = repr(request)

    assert "0xaddr" not in shown
    assert "0xsk" not in shown


def test_the_state_of_an_account_is_read_from_the_exchange(
    client_of: Client, platform: Platform, account_id: str, credentials: Credentials
) -> None:
    btc = Position("BTC", PositionSide.LONG, Decimal("0.01"), 2, Decimal(60000), Decimal(60550), Decimal("5.5"), None)
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
                "mark_price": "60550",
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
    btc = Position("BTC", PositionSide.LONG, Decimal("0.01"), 2, Decimal(60000), Decimal(60550), Decimal("5.5"), None)
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
    btc = Position("BTC", PositionSide.LONG, Decimal("0.01"), 2, Decimal(60000), Decimal(60550), Decimal("5.5"), None)
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
            "credentials": dict(credentials.values),
        },
    )

    assert response.status_code == 201


def test_the_user_gives_the_expiry_the_exchange_does_not_read_and_the_list_shows_its_state(
    client_of: Client, account_id: str
) -> None:
    anna = client_of("anna")

    response = anna.put(f"/accounts/{account_id}/expiry", json={"expires_on": "2026-12-08"})
    [listed] = anna.get("/accounts").json()
    details = anna.get(f"/accounts/{account_id}").json()

    assert response.status_code == 204
    assert (listed["expiry"], listed["expiry_status"], listed["days_left"], listed["expiry_editable"]) == (
        {"expires_on": "2026-12-08", "source": "entered"},
        "expiring",
        28,
        True,
    )
    assert details["expiry"] == listed["expiry"]


def test_the_expiry_the_exchange_reads_is_shown_and_cannot_be_given(
    client_of: Client, platform: Platform, account_id: str
) -> None:
    platform.hyperliquid.reads_expiry = True
    account = platform.account_named("anna", "test-1")
    platform.accounts.accounts[:] = [account.with_expiry(KeyExpiry.read(date(2026, 11, 9)))]
    anna = client_of("anna")

    response = anna.put(f"/accounts/{account_id}/expiry", json={"expires_on": "2026-12-08"})
    [listed] = anna.get("/accounts").json()

    assert (response.status_code, reason_of(response)) == (
        409,
        {"detail": "la scadenza di queste credenziali la legge l'exchange"},
    )
    assert (listed["expiry"], listed["expiry_status"], listed["days_left"], listed["expiry_editable"]) == (
        {"expires_on": "2026-11-09", "source": "read"},
        "expired",
        -1,
        False,
    )


def test_the_expiry_of_an_account_of_another_tenant_is_not_found(client_of: Client, account_id: str) -> None:
    response = client_of("bruno").put(f"/accounts/{account_id}/expiry", json={"expires_on": "2026-12-08"})

    assert response.status_code == 404


def test_the_replacement_carries_the_expiry_given_with_the_new_credentials(
    client_of: Client, platform: Platform, account_id: str, credentials: Credentials
) -> None:
    anna = client_of("anna")

    response = anna.put(
        f"/accounts/{account_id}/credentials", json={**rotated(platform, credentials), "expires_on": "2027-03-15"}
    )

    assert response.status_code == 200
    assert anna.get(f"/accounts/{account_id}").json()["expiry"] == {"expires_on": "2027-03-15", "source": "entered"}


def test_the_max_direction_exposure_is_set_shown_and_taken_away(client_of: Client, account_id: str) -> None:
    """R5.5.5, ADR esposizione-massima-per-direzione-del-conto."""
    anna = client_of("anna")

    set_response = anna.put(f"/accounts/{account_id}/max-direction-exposure", json={"percent": "62.5"})
    [listed] = anna.get("/accounts").json()
    removed = anna.put(f"/accounts/{account_id}/max-direction-exposure", json={"percent": None})
    details = anna.get(f"/accounts/{account_id}").json()

    assert (set_response.status_code, removed.status_code) == (204, 204)
    assert listed["max_direction_exposure_percent"] == "62.5"
    assert details["max_direction_exposure_percent"] is None


def test_a_max_direction_exposure_not_above_zero_is_refused_with_the_reason(client_of: Client, account_id: str) -> None:
    response = client_of("anna").put(f"/accounts/{account_id}/max-direction-exposure", json={"percent": "0"})

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "l'esposizione massima per direzione è maggiore di 0", "percent": "0"},
    )


def test_the_max_direction_exposure_of_an_account_of_another_tenant_is_not_found(
    client_of: Client, account_id: str
) -> None:
    response = client_of("bruno").put(f"/accounts/{account_id}/max-direction-exposure", json={"percent": "60"})

    assert response.status_code == 404


def test_the_reconciliation_interval_is_set_and_shown(client_of: Client, account_id: str) -> None:
    """ADR intervallo-di-riconciliazione-del-conto: the reading of the account always carries the interval."""
    anna = client_of("anna")

    before = anna.get(f"/accounts/{account_id}").json()
    response = anna.put(f"/accounts/{account_id}/reconciliation-interval", json={"minutes": 15})
    [listed] = anna.get("/accounts").json()

    assert before["reconciliation_interval_minutes"] == 5
    assert response.status_code == 204
    assert listed["reconciliation_interval_minutes"] == 15


@pytest.mark.parametrize("minutes", [0, 1441])
def test_a_reconciliation_interval_out_of_range_is_refused_with_the_reason(
    client_of: Client, account_id: str, minutes: int
) -> None:
    response = client_of("anna").put(f"/accounts/{account_id}/reconciliation-interval", json={"minutes": minutes})

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "intervallo di riconciliazione da 1 a 1440 minuti", "minutes": minutes},
    )


def test_the_reconciliation_interval_of_an_account_of_another_tenant_is_not_found(
    client_of: Client, account_id: str
) -> None:
    response = client_of("bruno").put(f"/accounts/{account_id}/reconciliation-interval", json={"minutes": 15})

    assert response.status_code == 404
