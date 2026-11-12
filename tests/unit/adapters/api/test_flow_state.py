from collections.abc import Callable
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, OidcSigningKeys
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.flow import Flow
from tests.support.activity import a_fill, a_position, an_activity
from tests.support.flows import a_configuration, a_flow, account_id_of
from tests.support.identity_provider import SETTINGS, IdentityProvider
from tests.support.platform import Platform
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
        Authentication(SETTINGS, verifier),
    )

    def client(user: str) -> TestClient:
        person = platform.directory.person(user)
        person.roles.add("Utente")
        return TestClient(api, headers={"Authorization": f"Bearer {provider.token_for(person)}"})

    return client


def flow_of(platform: Platform, user: str) -> Flow:
    account_id = account_id_of(platform, user)
    configuration = a_configuration(assets=("BTC",), allocated_capital=Decimal(500))
    flow = a_flow(platform.tenant_of(user), account_id=account_id, configuration=configuration)
    platform.flows.flows.append(flow)
    return flow


def test_the_state_of_a_flow_answers_its_attributed_values(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow, order = flow_of(platform, "anna"), uuid4()
    platform.platform_orders.add(order, flow.account_id, flow.id)
    platform.account_activity.activities[flow.account_id] = an_activity(
        positions=(a_position("BTC", margin=Decimal(100), unrealized_pnl=Decimal(12)), a_position("ETH")),
        fills=(a_fill("BTC", order, realized_pnl=Decimal(40), fee=Decimal(2)),),
    )

    response = anna.get(f"/flows/{flow.id.value}/state")

    assert response.status_code == 200
    assert response.json() == {
        "flow_id": str(flow.id.value),
        "currency": "USDC",
        "allocated_capital": "500",
        "available_liquidity": "438",
        "margin": "100",
        "unrealized_pnl": "12",
        "realized_pnl": "40",
        "fees": "2",
        "total_value": "550",
        "return_percent": "10",
        "positions": [{"asset": "BTC", "side": "long", "size": "1", "margin": "100", "unrealized_pnl": "12"}],
    }


def test_a_flow_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    theirs = flow_of(platform, "bruno")

    response = client_of("anna").get(f"/flows/{theirs.id.value}/state")

    assert (response.status_code, reason_of(response)) == (404, {"detail": "flusso non trovato"})


def test_an_exchange_that_cannot_be_read_answers_unavailable(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    platform.account_activity.activities[flow.account_id] = an_activity()
    platform.account_activity.reachable = False

    response = anna.get(f"/flows/{flow.id.value}/state")

    assert (response.status_code, reason_of(response)) == (503, {"detail": "exchange non raggiungibile, riprovare"})
