from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, OidcSigningKeys
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.order import OrderOrigin, OrderSource
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.verification.verification_run import VerificationRun
from tests.support.flows import a_configuration, a_flow
from tests.support.identity_provider import SETTINGS, IdentityProvider
from tests.support.platform import HYPERLIQUID, STARTED_AT, Platform, registration
from tests.support.steps import quoted

scenarios("E0-esecuzione-verificata/F0.4-procedura-di-verifica/R0.4.1-procedura-di-verifica-dell-esecuzione.feature")

EXCHANGE_REFUSAL = "Insufficient margin to place order. asset=0"


@dataclass
class Session:
    """The platform behind its API, as a user reaches it with a token of the identity provider."""

    platform: Platform = field(default_factory=Platform)
    identity_provider: IdentityProvider = field(default_factory=IdentityProvider)
    credentials: dict[str, Credentials] = field(default_factory=dict)
    response: httpx.Response | None = None

    def api(self) -> FastAPI:
        provider = self.identity_provider
        verifier = AccessTokenVerifier(SETTINGS, OidcSigningKeys(SETTINGS.discovery_url, provider.fetch))
        health = HealthReport(version="1.0.0", environment="dev")
        resolve_tenant = ResolveTenantUseCase(self.platform.tenants)
        return create_api(health, resolve_tenant, self.platform.for_tenant, Authentication(SETTINGS, verifier))

    def post_as(self, user: str, path: str) -> None:
        token = self.identity_provider.token_for(self.platform.directory.person(user))
        self.response = TestClient(self.api()).post(path, headers={"Authorization": f"Bearer {token}"})

    def answer(self, status: int) -> dict[str, Any]:
        assert self.response is not None, "no request was made"
        assert self.response.status_code == status, self.response.text
        body: dict[str, Any] = self.response.json()
        return body

    def step(self, name: str) -> dict[str, Any]:
        steps: list[dict[str, Any]] = [step for step in self.answer(200)["steps"] if step["step"] == name]
        (step,) = steps
        return step

    def access_of(self, account: str) -> TradingAccess:
        credentials = self.credentials[account]
        return TradingAccess(HYPERLIQUID, credentials.account_address, credentials.secret_key)

    def recorded_run(self, user: str) -> VerificationRun:
        (run,) = self.platform.runs_of(self.platform.tenant_of(user)).runs
        return run


@pytest.fixture
def session() -> Session:
    return Session()


@given(quoted('che "{user}" ha il conto "{account}" su "{exchange}" con margine disponibile di almeno 12 USDC'))
def user_has_account(session: Session, user: str, account: str, exchange: str) -> None:
    session.platform.directory.person(user).roles.add("Utente")
    session.credentials[account] = session.platform.accepted_credentials()
    session.platform.register_account(user, registration(account, exchange, session.credentials[account]))


@given(quoted('che il conto "{account}" non ha posizioni su "{coin}"'))
def account_without_position(session: Session, account: str, coin: str) -> None:
    assert session.platform.order_exchange.position(session.access_of(account), coin) is None


@given(quoted('che il conto "{account}" ha una posizione aperta su "{coin}"'))
def account_holds_position(session: Session, account: str, coin: str) -> None:
    position = HeldPosition(coin, Direction.SHORT, Decimal("0.0002"), 3)
    session.platform.order_exchange.hold(session.access_of(account), position)


@given(quoted('che sul conto "{account}" il flusso "{flow}" attivo ha l\'asset "{coin}"'))
def account_with_flow_on(session: Session, account: str, flow: str, coin: str) -> None:
    owner = session.platform.account_named("anna", account)
    configuration = a_configuration(assets=(coin,))
    session.platform.flows.flows.append(
        a_flow(
            owner.tenant_id, name=flow, status=FlowStatus.ACTIVE, account_id=owner.id.value, configuration=configuration
        )
    )


@given(parsers.re(r'^che il conto "(?P<account>[^"]+)" ha margine disponibile (?P<amount>\d+) USDC$'))
def account_with_margin(session: Session, account: str, amount: str) -> None:
    session.platform.hyperliquid.set_available_margin(session.credentials[account], Decimal(amount))


@given("che l'exchange rifiuta l'ordine di apertura")
def exchange_refuses_opening(session: Session) -> None:
    session.platform.order_exchange.rejection = EXCHANGE_REFUSAL


@given("che l'exchange esegue l'apertura e rifiuta la chiusura")
def exchange_refuses_closing(session: Session) -> None:
    session.platform.order_exchange.closing_rejection = EXCHANGE_REFUSAL


@when(quoted('"{user}" lancia la procedura di verifica sul conto "{account}"'))
def user_runs_verification(session: Session, user: str, account: str) -> None:
    account_id = session.platform.account_named(user, account).id.value
    session.post_as(user, f"/accounts/{account_id}/verifications")


@then(quoted('il passo "{name}" è riuscito'))
def step_succeeded(session: Session, name: str) -> None:
    step = session.step(name)
    assert step["succeeded"], step


@then(quoted('il passo "{name}" riporta una posizione long su "{coin}" con leva 2'))
def step_reads_long(session: Session, name: str, coin: str) -> None:
    step = session.step(name)
    assert step["succeeded"], step
    positions = [position for position in step["reading"]["positions"] if position["coin"] == coin]
    assert [(position["side"], position["leverage"]) for position in positions] == [("long", 2)]


@then(quoted('il passo "{name}" riporta nessuna posizione su "{coin}"'))
def step_reads_no_position(session: Session, name: str, coin: str) -> None:
    step = session.step(name)
    assert step["succeeded"], step
    assert [position for position in step["reading"]["positions"] if position["coin"] == coin] == []


@then(quoted('l\'esito complessivo della procedura è "{outcome}"'))
def overall_outcome(session: Session, outcome: str) -> None:
    assert session.answer(200)["outcome"] == outcome


@then("l'esito riporta la commissione totale pagata e il profitto o la perdita realizzati")
def outcome_reports_totals(session: Session) -> None:
    executions = session.platform.order_exchange.executions.values()
    body = session.answer(200)
    assert Decimal(body["total_fee"]) == sum((execution.fee for execution in executions), Decimal(0))
    assert Decimal(body["realized_pnl"]) == sum((execution.realized_pnl for execution in executions), Decimal(0))


@then(
    quoted(
        "dopo ogni passo saldo e posizioni letti dalla piattaforma coincidono con quelli mostrati dall'exchange "
        'per il conto "{account}"'
    )
)
def readings_match_exchange(session: Session, account: str) -> None:
    shown = session.platform.hyperliquid.shown[session.credentials[account]]
    readings = [step["reading"] for step in session.answer(200)["steps"] if step["reading"] is not None]
    # The readings of the steps are the last ones the exchange showed: before them came the check at the
    # registration of the account and the one before the procedure starts.
    assert len(readings) == 2
    for reading, state in zip(readings, shown[-2:], strict=True):
        assert Decimal(reading["balance"]) == state.balance.amount
        assert Decimal(reading["available_margin"]) == state.available_margin.amount
        assert [(p["coin"], p["side"], Decimal(p["size"]), p["leverage"]) for p in reading["positions"]] == [
            (p.coin, p.side.value, p.size, p.leverage) for p in state.positions
        ]


@then(quoted('la procedura non parte con il motivo "{reason}"'))
def verification_not_started(session: Session, reason: str) -> None:
    assert session.answer(409)["detail"] == reason
    assert session.platform.runs_of(session.platform.tenant_of("anna")).runs == []


@then("nessun ordine è inviato all'exchange")
def no_order_sent(session: Session) -> None:
    assert session.platform.order_exchange.sent == []


@then("l'esito riporta il messaggio originale dell'exchange")
def outcome_reports_exchange_message(session: Session) -> None:
    assert session.step("apertura long BTC leva 2")["message"] == EXCHANGE_REFUSAL


@then("i passi successivi non sono eseguiti")
def later_steps_not_run(session: Session) -> None:
    assert [step["step"] for step in session.answer(200)["steps"]] == ["apertura long BTC leva 2"]
    assert len(session.platform.order_exchange.sent) == 1


@then(quoted('l\'esito avverte che sul conto "{account}" resta aperta una posizione long su "{coin}"'))
def outcome_warns_open_position(session: Session, account: str, coin: str) -> None:
    body = session.answer(200)
    assert body["warning"] == f"sul conto resta aperta una posizione long su {coin}"
    assert body["account_id"] == str(session.platform.account_named("anna", account).id.value)
    held = session.platform.order_exchange.position(session.access_of(account), coin)
    assert held is not None
    assert held.direction is Direction.LONG


@then(
    quoted(
        'la procedura è registrata con l\'utente "{user}", il conto "{account}", l\'ambiente, l\'istante, '
        "l'esito di ogni passo e l'esito complessivo"
    )
)
def verification_recorded(session: Session, user: str, account: str) -> None:
    run = session.recorded_run(user)
    person = session.platform.directory.person(user)
    body = session.answer(200)
    assert (run.user_id, run.account_id) == (person.object_id, session.platform.account_named(user, account).id.value)
    assert (run.environment, run.started_at) == ("dev", STARTED_AT)
    assert [(step.step.value, step.succeeded) for step in run.steps] == [
        (step["step"], step["succeeded"]) for step in body["steps"]
    ]
    assert run.outcome == body["outcome"] == "superata"
    sources = {order.request.source for order in session.platform.orders_of(session.platform.tenant_of(user)).orders}
    assert sources == {OrderSource(OrderOrigin.VERIFICATION, person.object_id)}
