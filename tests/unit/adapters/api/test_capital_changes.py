"""The history of the capital of a flow and of an account through the API (R3.4.2, ADR
storico-delle-variazioni-di-capitale)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalCommand
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.capital_history import AccountTransfer, TransferDirection
from autotrading.domain.flows.flow import Flow
from tests.support.flows import a_configuration, a_flow, account_id_of
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
DEPOSITED_AT = datetime(2026, 11, 9, 8, 30, tzinfo=UTC)


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


def a_flow_of(platform: Platform, user: str) -> Flow:
    account_id = account_id_of(platform, user, balance=Decimal(5000))
    configuration = a_configuration(allocated_capital=Decimal(500))
    flow = a_flow(platform.tenant_of(user), account_id=account_id, configuration=configuration)
    platform.flows.flows.append(flow)
    platform.flows.save_version(flow)
    return flow


def changed(platform: Platform, user: str, flow: Flow, capital: int, at: datetime) -> None:
    platform.now = at
    command = ChangeAllocatedCapitalCommand(flow.id, Decimal(capital), platform.user_id_of(user))
    platform.use_cases_of(user).change_allocated_capital.execute(command)


def iso(instant: datetime) -> str:
    return instant.isoformat().replace("+00:00", "Z")


def test_the_history_of_a_flow_comes_in_a_page_from_the_most_recent_change(
    client_of: Client, platform: Platform
) -> None:
    flow = a_flow_of(platform, "anna")
    changed(platform, "anna", flow, 700, datetime(2026, 11, 10, 9, tzinfo=UTC))
    changed(platform, "anna", flow, 400, datetime(2026, 11, 15, 9, tzinfo=UTC))

    response = client_of("anna").get(f"/flows/{flow.id.value}/capital-changes")

    assert response.status_code == 200
    assert response.json() == {
        "page": 1,
        "has_next": False,
        "total": 2,
        "currency": "USDC",
        "changes": [
            {
                "changed_at": "2026-11-15T09:00:00Z",
                "flow_id": str(flow.id.value),
                "flow": "alfa",
                "reason": "riduzione",
                "amount": "300",
                "previous": "700",
                "new": "400",
            },
            {
                "changed_at": "2026-11-10T09:00:00Z",
                "flow_id": str(flow.id.value),
                "flow": "alfa",
                "reason": "aumento",
                "amount": "200",
                "previous": "500",
                "new": "700",
            },
        ],
    }


def test_the_history_of_a_flow_is_narrowed_to_the_days_asked(client_of: Client, platform: Platform) -> None:
    flow = a_flow_of(platform, "anna")
    changed(platform, "anna", flow, 700, datetime(2026, 11, 10, 9, tzinfo=UTC))
    changed(platform, "anna", flow, 400, datetime(2026, 11, 15, 9, tzinfo=UTC))

    response = client_of("anna").get(
        f"/flows/{flow.id.value}/capital-changes", params={"from": "2026-11-14", "to": "2026-11-16", "page": 1}
    )

    assert [change["changed_at"] for change in response.json()["changes"]] == ["2026-11-15T09:00:00Z"]
    assert response.json()["total"] == 1


def test_the_history_of_an_account_holds_its_flows_and_its_transfers(client_of: Client, platform: Platform) -> None:
    flow = a_flow_of(platform, "anna")
    account_id = account_id_of(platform, "anna")
    changed(platform, "anna", flow, 700, DEPOSITED_AT + timedelta(days=1))
    deposit = AccountTransfer(DEPOSITED_AT, Decimal("500.50"), TransferDirection.DEPOSIT)
    platform.account_transfers.declared[account_id] = [deposit]

    response = client_of("anna").get(f"/accounts/{account_id}/capital-changes")

    assert response.status_code == 200
    body = response.json()
    assert (body["page"], body["has_next"], body["total"]) == (1, False, 2)
    assert [change["reason"] for change in body["changes"]] == ["aumento", "deposito"]
    assert body["changes"][1] == {
        "changed_at": iso(DEPOSITED_AT),
        "flow_id": None,
        "flow": None,
        "reason": "deposito",
        "amount": "500.5",
        "previous": None,
        "new": None,
    }


def test_an_exchange_out_of_reach_answers_unavailable_rather_than_a_part_of_the_history(
    client_of: Client, platform: Platform
) -> None:
    account_id = account_id_of(platform, "anna")
    platform.account_transfers.reachable = False

    response = client_of("anna").get(f"/accounts/{account_id}/capital-changes")

    assert response.status_code == 503


def test_a_page_before_the_first_is_refused(client_of: Client, platform: Platform) -> None:
    flow = a_flow_of(platform, "anna")

    response = client_of("anna").get(f"/flows/{flow.id.value}/capital-changes", params={"page": 0})

    assert response.status_code == 400


def test_the_history_of_a_flow_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    theirs = a_flow_of(platform, "bruno")

    response = client_of("anna").get(f"/flows/{theirs.id.value}/capital-changes")

    assert response.status_code == 404
    assert reason_of(response)["detail"]


def test_the_history_of_an_account_the_tenant_does_not_have_is_not_found(client_of: Client, platform: Platform) -> None:
    missing = uuid4()
    platform.account_transfers.missing.add(missing)

    response = client_of("anna").get(f"/accounts/{missing}/capital-changes")

    assert response.status_code == 404
