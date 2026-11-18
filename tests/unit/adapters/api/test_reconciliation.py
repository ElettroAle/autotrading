"""The reconciliation of the balance of an account through the API: threshold, status, alarms, confirmation (R3.3.1),
and the record of what no flow explains (ADR movimenti-non-spiegati-nel-riquadro-del-conto).
"""

import base64
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.reconciliation import unattributable_cursor_of, unattributable_cursor_text
from autotrading.application.flows.errors import UnattributableCursorInvalidError
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.deviation_threshold import DeviationThreshold
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.flows.unattributable_page import UnattributableCursor
from tests.support.flows import account_id_of
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
READ_AT = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)
NOW = READ_AT + timedelta(hours=1)
COMPARISON = BalanceComparison(Decimal(1000), Decimal("980.5"), READ_AT)


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.now = NOW
    return platform


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


def alarm_on(platform: Platform, account_id: UUID) -> ReconciliationAlarm:
    platform.readings.save_reading(AccountReading(account_id, READ_AT, {}, Decimal(1000), COMPARISON))
    alarm = ReconciliationAlarm.of(account_id, COMPARISON)
    platform.readings.open(alarm)
    return alarm


def test_the_threshold_of_an_account_is_set(client_of: Client, platform: Platform) -> None:
    account_id = account_id_of(platform, "anna")

    response = client_of("anna").put(f"/accounts/{account_id}/deviation-threshold", json={"percent": "2.5"})

    assert response.status_code == 200
    assert response.json() == {"percent": "2.5"}
    assert platform.accounts_of("anna")[0].deviation_threshold == DeviationThreshold(Decimal("2.5"))


def test_a_threshold_out_of_range_is_refused_with_the_reason(client_of: Client, platform: Platform) -> None:
    account_id = account_id_of(platform, "anna")

    response = client_of("anna").put(f"/accounts/{account_id}/deviation-threshold", json={"percent": 101})

    assert response.status_code == 422
    assert reason_of(response) == {"detail": "la soglia di scostamento va da 0,1 a 100", "percent": "101"}


def test_the_threshold_of_an_account_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    account_id = account_id_of(platform, "bruno")

    response = client_of("anna").put(f"/accounts/{account_id}/deviation-threshold", json={"percent": 3})

    assert response.status_code == 404
    assert platform.accounts_of("bruno")[0].deviation_threshold == DeviationThreshold.default()


def test_the_reconciliation_of_an_account_with_an_alarm(client_of: Client, platform: Platform) -> None:
    account_id = account_id_of(platform, "anna")
    alarm_on(platform, account_id)

    response = client_of("anna").get(f"/accounts/{account_id}/reconciliation")

    assert response.status_code == 200
    assert response.json() == {
        "aligned": False,
        "threshold_percent": "1",
        "last_comparison": {
            "compared_at": "2026-11-16T10:00:00Z",
            "expected_balance": "1000",
            "read_balance": "980.5",
            "deviation_percent": "1.95",
        },
        "open_alarm": {
            "expected_balance": "1000",
            "read_balance": "980.5",
            "deviation_percent": "1.95",
            "opened_at": "2026-11-16T10:00:00Z",
            "confirmed_at": None,
        },
    }


def test_the_reconciliation_of_an_account_never_compared(client_of: Client, platform: Platform) -> None:
    account_id = account_id_of(platform, "anna")

    response = client_of("anna").get(f"/accounts/{account_id}/reconciliation")

    assert response.json() == {"aligned": True, "threshold_percent": "1", "last_comparison": None, "open_alarm": None}


def test_the_reconciliation_of_an_unknown_account_is_not_found(client_of: Client) -> None:
    response = client_of("anna").get(f"/accounts/{uuid4()}/reconciliation")

    assert response.status_code == 404


def test_the_confirmation_closes_the_alarm_and_the_list_keeps_it(client_of: Client, platform: Platform) -> None:
    account_id = account_id_of(platform, "anna")
    alarm_on(platform, account_id)
    anna = client_of("anna")

    confirmed = anna.post(f"/accounts/{account_id}/reconciliation/confirmation")
    alarms = anna.get(f"/accounts/{account_id}/reconciliation/alarms")

    assert confirmed.status_code == 204
    assert alarms.json() == [
        {
            "expected_balance": "1000",
            "read_balance": "980.5",
            "deviation_percent": "1.95",
            "opened_at": "2026-11-16T10:00:00Z",
            "confirmed_at": "2026-11-16T11:00:00Z",
        }
    ]
    assert anna.get(f"/accounts/{account_id}/reconciliation").json()["aligned"] is True


def test_a_confirmation_without_an_alarm_is_refused_with_the_reason(client_of: Client, platform: Platform) -> None:
    account_id = account_id_of(platform, "anna")

    response = client_of("anna").post(f"/accounts/{account_id}/reconciliation/confirmation")

    assert response.status_code == 409
    assert reason_of(response) == {"detail": "il conto test-1 non ha un allarme di riconciliazione aperto"}


def test_the_alarms_of_an_account_of_another_tenant_are_not_found(client_of: Client, platform: Platform) -> None:
    account_id = account_id_of(platform, "bruno")
    alarm_on(platform, account_id)

    alarms = client_of("anna").get(f"/accounts/{account_id}/reconciliation/alarms")
    confirmed = client_of("anna").post(f"/accounts/{account_id}/reconciliation/confirmation")

    assert (alarms.status_code, confirmed.status_code) == (404, 404)
    assert platform.readings.open_alarm(account_id) is not None
    assert AccountId(account_id) == platform.accounts_of("bruno")[0].id


# The record of what no flow explains


def recorded(platform: Platform, account_id: UUID, kind: UnattributableKind, minutes: int, amount: str) -> None:
    asset = None if kind is UnattributableKind.BALANCE_CHANGE else "SOL"
    reference = f"{kind.name}-{minutes}"
    item = UnattributableItem(account_id, kind, reference, asset, Decimal(amount), READ_AT + timedelta(minutes=minutes))
    platform.readings.record(item)


def test_the_record_of_an_account_comes_from_the_most_recent_with_the_net_of_its_changes(
    client_of: Client, platform: Platform
) -> None:
    account_id = account_id_of(platform, "anna")
    recorded(platform, account_id, UnattributableKind.BALANCE_CHANGE, 0, "-0.030")
    recorded(platform, account_id, UnattributableKind.POSITION, 1, "1.5")
    recorded(platform, account_id, UnattributableKind.BALANCE_CHANGE, 2, "0.05")

    response = client_of("anna").get(f"/accounts/{account_id}/reconciliation/unattributable")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"detected_at": "2026-11-16T10:02:00Z", "kind": "variazione del saldo", "asset": None, "amount": "0.05"},
            {"detected_at": "2026-11-16T10:01:00Z", "kind": "posizione", "asset": "SOL", "amount": "1.5"},
            {"detected_at": "2026-11-16T10:00:00Z", "kind": "variazione del saldo", "asset": None, "amount": "-0.03"},
        ],
        "next": None,
        "count": 3,
        "net_change": "0.02",
    }


def test_the_record_is_narrowed_by_kind_and_period(client_of: Client, platform: Platform) -> None:
    account_id = account_id_of(platform, "anna")
    recorded(platform, account_id, UnattributableKind.BALANCE_CHANGE, 0, "4")
    recorded(platform, account_id, UnattributableKind.POSITION, 1, "1.5")
    recorded(platform, account_id, UnattributableKind.BALANCE_CHANGE, 10, "-1")
    period = {"since": "2026-11-16T10:00:00Z", "until": "2026-11-16T10:10:00Z"}

    response = client_of("anna").get(
        f"/accounts/{account_id}/reconciliation/unattributable", params={"kind": "variazione del saldo", **period}
    )

    assert [item["amount"] for item in response.json()["items"]] == ["4"]
    assert (response.json()["count"], response.json()["net_change"]) == (1, "4")


def test_the_next_page_of_the_record_starts_after_the_last_case_seen(client_of: Client, platform: Platform) -> None:
    account_id = account_id_of(platform, "anna")
    for minutes in range(51):
        recorded(platform, account_id, UnattributableKind.BALANCE_CHANGE, minutes, "1")
    anna = client_of("anna")

    first = anna.get(f"/accounts/{account_id}/reconciliation/unattributable").json()
    second = anna.get(f"/accounts/{account_id}/reconciliation/unattributable", params={"cursor": first["next"]}).json()

    assert (len(first["items"]), first["count"], first["net_change"]) == (50, 51, "51")
    assert [item["detected_at"] for item in second["items"]] == ["2026-11-16T10:00:00Z"]
    assert second["next"] is None


def test_an_unknown_kind_is_refused(client_of: Client, platform: Platform) -> None:
    account_id = account_id_of(platform, "anna")

    response = client_of("anna").get(f"/accounts/{account_id}/reconciliation/unattributable", params={"kind": "x"})

    assert response.status_code == 422


@pytest.mark.parametrize("cursor", ["non-base64!", base64.urlsafe_b64encode(b"2026-11-12|x").decode(), "YQ=="])
def test_a_page_after_an_unreadable_case_is_refused(client_of: Client, platform: Platform, cursor: str) -> None:
    account_id = account_id_of(platform, "anna")

    response = client_of("anna").get(f"/accounts/{account_id}/reconciliation/unattributable", params={"cursor": cursor})

    assert response.status_code == 422
    assert reason_of(response) == {"detail": "pagina dei movimenti non spiegati non valida"}


def test_the_cursor_of_a_page_of_the_record_reads_back_as_the_same_case() -> None:
    cursor = UnattributableCursor(READ_AT, uuid4())

    assert unattributable_cursor_of(unattributable_cursor_text(cursor)) == cursor


def test_a_cursor_of_the_record_that_is_not_text_is_refused() -> None:
    with pytest.raises(UnattributableCursorInvalidError):
        unattributable_cursor_of(base64.urlsafe_b64encode(bytes([0xFF, 0xFE])).decode())


def test_the_record_of_an_account_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    account_id = account_id_of(platform, "bruno")
    recorded(platform, account_id, UnattributableKind.BALANCE_CHANGE, 0, "1")

    response = client_of("anna").get(f"/accounts/{account_id}/reconciliation/unattributable")

    assert response.status_code == 404
