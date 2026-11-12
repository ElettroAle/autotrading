from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, OidcSigningKeys
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.trade_intent import TradeSide
from tests.support.flows import a_flow
from tests.support.identity_provider import SETTINGS, IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
OPENED = datetime(2026, 11, 12, 10, tzinfo=UTC)


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
    flow = a_flow(platform.tenant_of(user))
    platform.flows.flows.append(flow)
    return flow


def a_position(flow: Flow, closed_after: timedelta, reason: CloseReason = CloseReason.AGENT) -> ClosedPosition:
    return ClosedPosition(
        tenant_id=flow.tenant_id,
        flow_id=flow.id,
        asset="BTC",
        side=TradeSide.LONG,
        leverage=2,
        margin=Decimal(50),
        opening=PositionEnd(Decimal(100000), OPENED, OPENED),
        closing=PositionEnd(Decimal(102000), OPENED + closed_after),
        fees=Decimal("0.08"),
        reason=reason,
    )


def test_the_closed_positions_of_a_flow_answer_with_their_result(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    platform.closed_positions.positions.append(a_position(flow, timedelta(hours=2, minutes=30)))

    response = anna.get(f"/flows/{flow.id.value}/closed-positions")

    assert response.status_code == 200
    assert response.json() == [
        {
            "asset": "BTC",
            "side": "long",
            "leverage": 2,
            "margin": "50",
            "open_price": "100000",
            "close_price": "102000",
            "opened_at": "2026-11-12T10:00:00Z",
            "closed_at": "2026-11-12T12:30:00Z",
            "duration_seconds": 9000,
            "pnl": "2",
            "pnl_percent_of_margin": "4",
            "fees": "0.08",
            "reason": "decisione dell'agente",
            "opening_cycle": "2026-11-12T10:00:00Z",
            "closing_cycle": None,
        }
    ]


def test_the_closed_positions_answer_from_the_most_recent_close(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    platform.closed_positions.positions.extend(
        a_position(flow, timedelta(hours=hours), CloseReason.MANUAL) for hours in (1, 3)
    )

    body = anna.get(f"/flows/{flow.id.value}/closed-positions").json()

    assert [position["closed_at"] for position in body] == ["2026-11-12T13:00:00Z", "2026-11-12T11:00:00Z"]
    assert {position["reason"] for position in body} == {"comando manuale"}


def test_the_closed_positions_of_a_flow_of_another_user_do_not_exist(client_of: Client, platform: Platform) -> None:
    flow = flow_of(platform, "bruno")
    platform.closed_positions.positions.append(a_position(flow, timedelta(hours=1)))

    response = client_of("anna").get(f"/flows/{flow.id.value}/closed-positions")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "flusso non trovato"}
