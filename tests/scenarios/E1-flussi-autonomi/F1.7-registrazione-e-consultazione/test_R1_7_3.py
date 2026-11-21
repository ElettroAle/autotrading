from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.adapters.outbound.process_memory.account_activity import (
    ProcessMemoryAccountActivityAdapter,
    _AccountActivityStore,
)
from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.support.activity import an_activity

# The steps of the record and of the consultation of the cycles are shared by R1.7.1, R1.7.3 and R1.4.6.
from tests.support.record_steps import *  # noqa: F403
from tests.support.record_steps import overviews
from tests.support.records import Records
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.7-registrazione-e-consultazione/R1.7.3-consultazione-di-flussi-e-cicli.feature")

# What the API process keeps of a reading of an account: the owner chose 10 seconds (ADR
# cache-delle-letture-del-conto-come-decorator-in-memoria).
VALIDITY_SECONDS = 10.0


class ApiReadings:
    """The readings of the accounts the API asks for the dashboard, through the decorator its composition mounts.

    An account has one identifier by its name for every user: tenants that ask for the same account still never share
    its reading, which proves the reading is kept by tenant and not only by account.
    """

    def __init__(self) -> None:
        self.exchange = FakeAccountActivityAdapter()
        self.seconds = 1000.0
        self.store = _AccountActivityStore(VALIDITY_SECONDS, lambda: self.seconds)
        self.accounts: dict[str, UUID] = {}
        self.tenants: dict[str, TenantId] = {}
        self.answers: list[AccountActivity | AutotradingError] = []

    def account(self, name: str) -> UUID:
        if name not in self.accounts:
            self.accounts[name] = uuid4()
            self.exchange.activities[self.accounts[name]] = an_activity(balance=Decimal(1000 + len(self.accounts)))
        return self.accounts[name]

    def consult(self, user: str, account: str) -> None:
        tenant_id = self.tenants.setdefault(user, TenantId.new())
        reading = ProcessMemoryAccountActivityAdapter(self.exchange, tenant_id, self.store)
        try:
            self.answers.append(reading.execute(self.account(account)))
        except AutotradingError as error:
            self.answers.append(error)


@pytest.fixture
def readings() -> ApiReadings:
    return ApiReadings()


@given(quoted('che "{user}" ha il flusso "{flow}" in pausa automatica con il motivo "{reason}"'))
def flow_paused_automatically(records: Records, user: str, flow: str, reason: str) -> None:
    records.add_flow(user, flow)
    store = records.platform.flows
    paused = next(each for each in store.flows if each.name.value == flow)
    store.flows[store.flows.index(paused)] = replace(paused, status=FlowStatus.PAUSED)
    store.pause_reasons[paused.id] = reason


@then(
    quoted(
        'l\'elenco contiene il flusso "{flow}" con conto "{account}", ambiente "{environment}", stato "{status}", '
        'motivo della pausa "{reason}" e modello "{model}"'
    )
)
def flow_listed_with_details(
    records: Records, *, flow: str, account: str, environment: str, status: str, reason: str, model: str
) -> None:
    [overview] = [overview for overview in overviews(records) if overview.summary.name == flow]
    summary = overview.summary
    assert (summary.account, overview.environment, summary.status) == (account, environment, status)
    assert (summary.pause_reason, summary.model) == (reason, model)


@given(quoted('che "{user}" consulta il conto "{account}" dall\'API'))
@when(quoted('"{user}" consulta il conto "{account}" dall\'API'))
def consults_account(readings: ApiReadings, user: str, account: str) -> None:
    readings.consult(user, account)


@when(
    parsers.re(
        r'^"(?P<user>[^"]+)" consulta di nuovo il conto "(?P<account>[^"]+)" dall\'API '
        r"dopo (?P<seconds>\d+) second[oi]$"
    )
)
def consults_again(readings: ApiReadings, user: str, account: str, seconds: str) -> None:
    readings.seconds += int(seconds)
    readings.consult(user, account)


@given(quoted('che l\'exchange non risponde alla lettura del conto "{account}"'))
def exchange_silent(readings: ApiReadings, account: str) -> None:
    readings.account(account)
    readings.exchange.reachable = False


@when("l'exchange torna a rispondere")
def exchange_back(readings: ApiReadings) -> None:
    readings.exchange.reachable = True


@then(parsers.re(r'^l\'exchange ha letto il conto "(?P<account>[^"]+)" (?P<count>\d+) volt[ae]$'))
def exchange_read(readings: ApiReadings, account: str, count: str) -> None:
    assert readings.exchange.read.count(readings.accounts[account]) == int(count)


@then("le due consultazioni riportano la stessa lettura")
def same_reading(readings: ApiReadings) -> None:
    first, second = readings.answers
    assert isinstance(first, AccountActivity)
    assert second == first


@then("la prima consultazione risponde che l'exchange non è raggiungibile e la seconda riporta la lettura")
def failure_then_reading(readings: ApiReadings) -> None:
    first, second = readings.answers
    assert isinstance(first, FlowExchangeUnavailableError)
    assert isinstance(second, AccountActivity)
