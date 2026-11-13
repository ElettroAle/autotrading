from dataclasses import dataclass, field
from decimal import Decimal

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.order import OrderOrigin, OrderSource
from autotrading.domain.orders.trading_access import TradingAccess
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import HYPERLIQUID, Platform, registration
from tests.support.steps import quoted

scenarios("E0-esecuzione-verificata/F0.3-esecuzione-degli-ordini/R0.3.2-chiusura-manuale-di-una-posizione.feature")


@dataclass
class Session:
    """The platform behind its API, as a user reaches it with a token of the identity provider."""

    platform: Platform = field(default_factory=Platform)
    identity_provider: IdentityProvider = field(default_factory=IdentityProvider)
    credentials: dict[str, Credentials] = field(default_factory=dict)
    response: httpx.Response | None = None

    def api(self) -> FastAPI:
        provider = self.identity_provider
        health = HealthReport(version="1.0.0", environment="dev")
        resolve_tenant = ResolveTenantUseCase(self.platform.tenants)
        return create_api(health, resolve_tenant, self.platform.for_tenant, provider.authentication())

    def post_as(self, user: str, path: str, body: object = None) -> None:
        token = self.identity_provider.token_for(self.platform.directory.person(user))
        self.response = TestClient(self.api()).post(path, json=body, headers={"Authorization": f"Bearer {token}"})

    def answer(self, status: int) -> dict[str, object]:
        assert self.response is not None, "no request was made"
        assert self.response.status_code == status, self.response.text
        body: dict[str, object] = self.response.json()
        return body

    def access_of(self, account: str) -> TradingAccess:
        credentials = self.credentials[account]
        return TradingAccess(HYPERLIQUID, credentials.account_address, credentials.secret_key)

    def closing_execution(self) -> Execution:
        return self.platform.order_exchange.executions[self.platform.order_exchange.sent[-1].id]


@pytest.fixture
def session() -> Session:
    return Session()


@given(quoted('che "{user}" ha il conto "{account}" su "{exchange}"'))
def user_has_account(session: Session, user: str, account: str, exchange: str) -> None:
    session.platform.directory.person(user).roles.add("Utente")
    session.credentials[account] = session.platform.accepted_credentials()
    session.platform.register_account(user, registration(account, exchange, session.credentials[account]))


@given(quoted('che il conto "{account}" ha una posizione long su "{coin}"'))
def account_holds_long(session: Session, account: str, coin: str) -> None:
    position = HeldPosition(coin, Direction.LONG, Decimal("0.0002"), 2)
    session.platform.order_exchange.hold(session.access_of(account), position)


@given(quoted('che il conto "{account}" non ha posizioni su "{coin}"'))
def account_without_position(session: Session, account: str, coin: str) -> None:
    assert session.platform.order_exchange.position(session.access_of(account), coin) is None


@when(quoted('"{user}" chiude la posizione su "{coin}" del conto "{account}"'))
def user_closes(session: Session, user: str, coin: str, account: str) -> None:
    account_id = session.platform.account_named(user, account).id.value
    session.post_as(user, f"/accounts/{account_id}/positions/{coin}/close")


@when(quoted('"{user}" chiede di aprire una posizione su "{coin}" del conto "{account}"'))
def user_asks_to_open(session: Session, user: str, coin: str, account: str) -> None:
    account_id = session.platform.account_named(user, account).id.value
    session.post_as(user, f"/accounts/{account_id}/positions", {"coin": coin, "direction": "long", "leverage": 2})


@then(quoted('sull\'exchange il conto "{account}" non ha posizioni su "{coin}"'))
def exchange_without_position(session: Session, account: str, coin: str) -> None:
    session.answer(200)
    assert session.platform.order_exchange.positions.get((session.access_of(account).account_address, coin)) is None


@then("l'esito riporta il prezzo medio di chiusura")
def outcome_reports_average_price(session: Session) -> None:
    assert session.answer(200)["average_price"] == str(session.closing_execution().average_price)


@then("l'esito riporta il profitto o la perdita realizzati")
def outcome_reports_realized_pnl(session: Session) -> None:
    assert session.answer(200)["realized_pnl"] == str(session.closing_execution().realized_pnl)


@then("l'esito riporta la commissione pagata")
def outcome_reports_fee(session: Session) -> None:
    assert session.answer(200)["fee"] == str(session.closing_execution().fee)


@then(quoted('la chiusura è registrata con il motivo "{origin}" e l\'utente "{user}"'))
def close_recorded(session: Session, origin: str, user: str) -> None:
    (order,) = session.platform.orders_of(session.platform.tenant_of(user)).orders
    person = session.platform.directory.person(user)
    assert order.request.source == OrderSource(OrderOrigin(origin), person.object_id)
    assert order.request.market_order.reduce_only


@then(quoted('la richiesta fallisce con il motivo "{reason}"'))
def request_fails(session: Session, reason: str) -> None:
    assert session.answer(409)["detail"] == reason


@then(quoted('la richiesta è respinta con il motivo "{reason}"'))
def request_refused(session: Session, reason: str) -> None:
    assert session.answer(403)["detail"] == reason


@then("nessun ordine è inviato all'exchange")
def no_order_sent(session: Session) -> None:
    assert session.platform.order_exchange.sent == []
