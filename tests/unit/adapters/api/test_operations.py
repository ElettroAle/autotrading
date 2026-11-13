import base64
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.operations import cursor_of, cursor_text
from autotrading.application.flows.errors import OperationsCursorInvalidError
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import (
    AccountLedger,
    Execution,
    ExecutionKind,
    FundingEntry,
    FundingPayment,
    LedgerEntry,
)
from autotrading.domain.flows.operations import OperationCursor, OperationSource
from tests.support.flows import a_flow, account_id_of
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
NOON = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
CRLF = "\r\n"


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


def flow_of(platform: Platform, user: str) -> Flow:
    flow = a_flow(platform.tenant_of(user), account_id=account_id_of(platform, user))
    platform.flows.flows.append(flow)
    return flow


def an_execution(fill_id: str, size: Decimal, executed_at: datetime, asset: str = "BTC") -> Execution:
    return Execution(
        fill_id,
        f"o-{fill_id}",
        None,
        asset,
        size,
        Decimal("100.50"),
        Decimal("0.10"),
        Decimal("3.00"),
        Decimal(0),
        False,
        executed_at,
    )


def record(
    platform: Platform,
    account_id: UUID,
    flow_id: FlowId | None,
    *executions: Execution,
    funding: tuple[FundingPayment, ...] = (),
) -> None:
    kind = ExecutionKind.UNATTRIBUTED if flow_id is None else ExecutionKind.FLOW_ORDER
    entries = tuple(LedgerEntry(execution, flow_id, kind) for execution in executions)
    payments = tuple(FundingEntry(payment, flow_id) for payment in funding)
    platform.ledger.record(account_id, AccountLedger(entries, payments), NOON)


def test_the_operations_of_a_flow_answer_executions_and_funding_newest_first(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    record(
        platform,
        flow.account_id,
        flow.id,
        an_execution("acquisto", Decimal(2), NOON),
        an_execution("vendita", Decimal("-0.5"), NOON + timedelta(minutes=1)),
        funding=(FundingPayment("BTC", Decimal("-0.25"), NOON + timedelta(minutes=2)),),
    )

    response = anna.get(f"/flows/{flow.id.value}/operations")

    assert response.status_code == 200
    assert response.json() == {
        "operations": [
            {
                "occurred_at": "2026-11-12T12:02:00Z",
                "flow": "alfa",
                "asset": "BTC",
                "kind": "funding",
                "side": None,
                "size": None,
                "price": None,
                "fee": "0",
                "realized_pnl": "0",
                "funding": "-0.25",
            },
            {
                "occurred_at": "2026-11-12T12:01:00Z",
                "flow": "alfa",
                "asset": "BTC",
                "kind": ExecutionKind.FLOW_ORDER.value,
                "side": "vendita",
                "size": "0.5",
                "price": "100.5",
                "fee": "0.1",
                "realized_pnl": "3",
                "funding": "0",
            },
            {
                "occurred_at": "2026-11-12T12:00:00Z",
                "flow": "alfa",
                "asset": "BTC",
                "kind": ExecutionKind.FLOW_ORDER.value,
                "side": "acquisto",
                "size": "2",
                "price": "100.5",
                "fee": "0.1",
                "realized_pnl": "3",
                "funding": "0",
            },
        ],
        "next": None,
        "totals": {"count": 3, "realized_pnl": "6", "fees": "0.2", "funding": "-0.25"},
    }


def test_the_next_page_of_a_flow_starts_after_the_last_operation_seen(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    executions = [an_execution(f"f-{minute}", Decimal(1), NOON + timedelta(minutes=minute)) for minute in range(51)]
    record(platform, flow.account_id, flow.id, *executions)

    first = anna.get(f"/flows/{flow.id.value}/operations").json()
    second = anna.get(f"/flows/{flow.id.value}/operations", params={"after": first["next"]}).json()

    assert len(first["operations"]) == 50
    assert first["operations"][0]["occurred_at"] == "2026-11-12T12:50:00Z"
    assert [row["occurred_at"] for row in second["operations"]] == ["2026-11-12T12:00:00Z"]
    assert second["next"] is None


def test_the_operations_of_a_flow_are_filtered_by_asset_and_by_period(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    record(
        platform,
        flow.account_id,
        flow.id,
        an_execution("prima", Decimal(1), NOON - timedelta(hours=1)),
        an_execution("dentro", Decimal(1), NOON),
        an_execution("altro-asset", Decimal(1), NOON, asset="ETH"),
        an_execution("alla-fine", Decimal(1), NOON + timedelta(hours=1)),
    )
    params = {"asset": "BTC", "from": "2026-11-12T12:00:00Z", "to": "2026-11-12T13:00:00Z"}

    response = anna.get(f"/flows/{flow.id.value}/operations", params=params)

    assert [(row["asset"], row["occurred_at"]) for row in response.json()["operations"]] == [
        ("BTC", "2026-11-12T12:00:00Z")
    ]


def test_the_operations_of_a_flow_of_another_tenant_are_not_found(client_of: Client, platform: Platform) -> None:
    theirs = flow_of(platform, "bruno")

    response = client_of("anna").get(f"/flows/{theirs.id.value}/operations")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "flusso non trovato"}


def test_the_operations_of_an_account_are_those_of_no_flow(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    record(platform, flow.account_id, flow.id, an_execution("del-flusso", Decimal(1), NOON))
    record(platform, flow.account_id, None, an_execution("fuori", Decimal(3), NOON, asset="SOL"))

    response = anna.get(f"/accounts/{flow.account_id}/operations")

    assert response.status_code == 200
    rows = [(row["asset"], row["kind"], row["size"], row["flow"]) for row in response.json()["operations"]]
    assert rows == [("SOL", ExecutionKind.UNATTRIBUTED.value, "3", None)]


def test_all_the_operations_of_an_account_name_their_flow(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    record(platform, flow.account_id, flow.id, an_execution("del-flusso", Decimal(1), NOON))
    record(platform, flow.account_id, None, an_execution("fuori", Decimal(3), NOON + timedelta(minutes=1), "SOL"))

    response = anna.get(f"/accounts/{flow.account_id}/operations", params={"scope": "all"})

    body = response.json()
    assert [(row["asset"], row["flow"]) for row in body["operations"]] == [("SOL", None), ("BTC", "alfa")]
    assert body["totals"] == {"count": 2, "realized_pnl": "6", "fees": "0.2", "funding": "0"}


def test_an_unknown_scope_of_an_account_is_refused(client_of: Client, platform: Platform) -> None:
    flow = flow_of(platform, "anna")

    response = client_of("anna").get(f"/accounts/{flow.account_id}/operations", params={"scope": "qualcuna"})

    assert response.status_code == 422


def test_the_export_of_a_flow_is_csv_of_every_row_of_the_filter_oldest_first(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    executions = [an_execution(f"f-{minute}", Decimal(1), NOON + timedelta(minutes=minute)) for minute in range(51)]
    funding = (FundingPayment("BTC", Decimal("-0.25"), NOON + timedelta(seconds=30)),)
    record(platform, flow.account_id, flow.id, an_execution("vendita", Decimal("-0.5"), NOON - timedelta(hours=1)))
    record(platform, flow.account_id, flow.id, *executions, funding=funding)

    response = anna.get(f"/flows/{flow.id.value}/operations.csv", params={"from": "2026-11-12T12:00:00Z"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == 'attachment; filename="operazioni.csv"'
    lines = response.text.split(CRLF)
    assert lines[0] == "istante,flusso,asset,tipo,lato,quantità,prezzo,commissione,PnL realizzato,funding"
    assert lines[1] == f"2026-11-12T12:00:00+00:00,alfa,BTC,{ExecutionKind.FLOW_ORDER.value},acquisto,1,100.5,0.1,3,0"
    assert lines[2] == "2026-11-12T12:00:30+00:00,alfa,BTC,funding,,,,0,0,-0.25"
    assert len(lines) == 1 + 52 + 1
    assert lines[-1] == ""


def test_the_export_of_an_account_names_the_rows_of_no_flow(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    record(platform, flow.account_id, None, an_execution("fuori", Decimal("-2"), NOON, "SOL"))

    response = anna.get(f"/accounts/{flow.account_id}/operations.csv", params={"scope": "all"})

    sold = f"2026-11-12T12:00:00+00:00,nessun flusso,SOL,{ExecutionKind.UNATTRIBUTED.value},vendita,2,100.5,0.1,3,0"
    assert response.text.split(CRLF)[1] == sold


def test_the_export_of_a_flow_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    theirs = flow_of(platform, "bruno")

    response = client_of("anna").get(f"/flows/{theirs.id.value}/operations.csv")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "flusso non trovato"}


def test_the_export_of_an_account_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    theirs = account_id_of(platform, "bruno")

    response = client_of("anna").get(f"/accounts/{theirs}/operations.csv")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "conto non trovato"}


def test_the_operations_of_an_account_of_another_tenant_are_not_found(client_of: Client, platform: Platform) -> None:
    theirs = account_id_of(platform, "bruno")

    response = client_of("anna").get(f"/accounts/{theirs}/operations")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "conto non trovato"}


def test_the_operations_of_an_unknown_account_are_not_found(client_of: Client) -> None:
    response = client_of("anna").get(f"/accounts/{uuid4()}/operations")

    assert response.status_code == 404


@pytest.mark.parametrize("after", ["non-base64!", base64.urlsafe_b64encode(b"2026-11-12|x|1").decode(), "YQ=="])
def test_a_page_after_an_unreadable_operation_is_refused(client_of: Client, platform: Platform, after: str) -> None:
    flow = flow_of(platform, "anna")

    response = client_of("anna").get(f"/flows/{flow.id.value}/operations", params={"after": after})

    assert response.status_code == 422
    assert reason_of(response) == {"detail": "pagina delle operazioni non valida"}


def test_the_cursor_of_a_page_reads_back_as_the_same_operation() -> None:
    cursor = OperationCursor(NOON, OperationSource.FUNDING, 42)

    assert cursor_of(cursor_text(cursor)) == cursor


def test_a_cursor_that_is_not_text_is_refused() -> None:
    with pytest.raises(OperationsCursorInvalidError):
        cursor_of(base64.urlsafe_b64encode(bytes([0xFF, 0xFE])).decode())
