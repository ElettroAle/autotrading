from dataclasses import replace
from uuid import UUID

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.read_free_capital import ReadFreeCapitalCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.free_capital import FreeCapital

# The steps of the record and of the consultation of the cycles are shared by R1.7.1, R1.7.3 and R1.4.6.
from tests.support.record_steps import *  # noqa: F403
from tests.support.record_steps import overviews
from tests.support.records import Records
from tests.support.steps import quoted

scenarios(
    "E1-flussi-autonomi/F1.7-registrazione-e-consultazione/R1.7.3-consultazione-di-flussi-e-cicli/api/R1.7.3-consultazione-di-flussi-e-cicli.feature"
)

# What the API process keeps of a reading of an account: the owner chose 10 seconds (ADR
# cache-delle-letture-del-conto-come-decorator-in-memoria).
VALIDITY_SECONDS = 10.0


class ApiReadings:
    """The account as the dashboard consults it from the API: the use case of its free capital, which reads the account
    through the memory the composition of the API mounts on the reading.

    Every user registers its own account by the name the scenario gives, so "test-1" of two users are two accounts.
    """

    def __init__(self, records: Records) -> None:
        self.records = records
        self.platform = records.platform
        self.platform.remembered_readings.validity_seconds = VALIDITY_SECONDS
        self.accounts: dict[str, list[UUID]] = {}
        self.answers: list[FreeCapital | AutotradingError] = []
        self.reads: list[UUID] = []

    def account(self, user: str, name: str) -> UUID:
        account_id = self.records.flow_cycles.account_of(user, name)
        known = self.accounts.setdefault(name, [])
        if account_id not in known:
            known.append(account_id)
        return account_id

    def consult(self, user: str, account: str) -> None:
        command = ReadFreeCapitalCommand(self.account(user, account))
        exchange = self.platform.account_activity
        before = len(exchange.read)
        try:
            self.answers.append(self.records.use_cases_of(user).read_free_capital.execute(command))
        except AutotradingError as error:
            self.answers.append(error)
        self.reads.extend(exchange.read[before:])

    def read_count(self, account: str) -> int:
        return sum(self.reads.count(account_id) for account_id in self.accounts[account])


@pytest.fixture
def readings(records: Records) -> ApiReadings:
    return ApiReadings(records)


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
    readings.platform.remembered_readings.seconds += int(seconds)
    readings.consult(user, account)


@given(quoted('che l\'exchange non risponde alla lettura del conto "{account}"'))
def exchange_silent(readings: ApiReadings, account: str) -> None:
    readings.account("anna", account)
    readings.platform.account_activity.reachable = False


@when("l'exchange torna a rispondere")
def exchange_back(readings: ApiReadings) -> None:
    readings.platform.account_activity.reachable = True


@then(parsers.re(r'^l\'exchange ha letto il conto "(?P<account>[^"]+)" (?P<count>\d+) volt[ae]$'))
def exchange_read(readings: ApiReadings, account: str, count: str) -> None:
    assert readings.read_count(account) == int(count)


@then("le due consultazioni riportano la stessa lettura")
def same_reading(readings: ApiReadings) -> None:
    first, second = readings.answers
    assert isinstance(first, FreeCapital)
    assert second == first


@then("la prima consultazione risponde che l'exchange non è raggiungibile e la seconda riporta la lettura")
def failure_then_reading(readings: ApiReadings) -> None:
    first, second = readings.answers
    assert isinstance(first, FlowExchangeUnavailableError)
    assert isinstance(second, FreeCapital)
