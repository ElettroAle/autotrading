from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.verification.errors import VerificationAccountNotFoundError, VerificationStepError
from autotrading.application.verification.run_exchange_verification import (
    RunExchangeVerificationCommand,
    RunExchangeVerificationUseCase,
)
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.errors import AssetOfFlowError, InsufficientMarginError, PositionAlreadyOpenError
from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.procedure import PROCEDURE_OPENING, Opening, Step
from autotrading.domain.verification.reading import AccountReading
from tests.fakes.verification_run_repository import InMemoryVerificationRunRepositoryAdapter
from tests.support.verification import CLOSED, LONG_BTC, OPENED, REFUSED, STARTED_AT, a_reading

ANNA = UserId("oid-anna")
UNREACHABLE = "exchange non raggiungibile"

Answer = AccountReading | Exception


@dataclass
class ScriptedReadings:
    """Answers the readings in order: the check before starting, then the reading steps."""

    answers: list[Answer]
    asked: list[UUID] = field(default_factory=list)
    flows: dict[tuple[UUID, str], str] = field(default_factory=dict)

    def read(self, account_id: UUID) -> AccountReading:
        self.asked.append(account_id)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def flow_on(self, account_id: UUID, asset: str) -> str | None:
        return self.flows.get((account_id, asset))


@dataclass
class ScriptedOrders:
    opening: OrderResult | Exception = OPENED
    closing: OrderResult | Exception = CLOSED
    sent: list[tuple[str, UUID, object, UserId]] = field(default_factory=list)

    def open(self, account_id: UUID, opening: Opening, user_id: UserId) -> OrderResult:
        self.sent.append(("open", account_id, opening, user_id))
        return _answer(self.opening)

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderResult:
        self.sent.append(("close", account_id, coin, user_id))
        return _answer(self.closing)


def _answer(answer: OrderResult | Exception) -> OrderResult:
    if isinstance(answer, Exception):
        raise answer
    return answer


def normal_readings() -> list[Answer]:
    return [a_reading(), a_reading(LONG_BTC), a_reading()]


Build = Callable[..., RunExchangeVerificationUseCase]


@pytest.fixture
def runs() -> InMemoryVerificationRunRepositoryAdapter:
    return InMemoryVerificationRunRepositoryAdapter()


@pytest.fixture
def build(runs: InMemoryVerificationRunRepositoryAdapter) -> Build:
    def use_case(readings: ScriptedReadings, orders: ScriptedOrders) -> RunExchangeVerificationUseCase:
        return RunExchangeVerificationUseCase(readings, orders, runs, "prod", lambda: STARTED_AT)

    return use_case


def test_a_passed_run_opens_reads_closes_reads_and_is_recorded(
    build: Build, runs: InMemoryVerificationRunRepositoryAdapter
) -> None:
    account_id, readings, orders = uuid4(), ScriptedReadings(normal_readings()), ScriptedOrders()

    run = build(readings, orders).execute(RunExchangeVerificationCommand(account_id, ANNA))

    assert [(step.step, step.succeeded) for step in run.steps] == [(step, True) for step in Step]
    assert orders.sent == [("open", account_id, PROCEDURE_OPENING, ANNA), ("close", account_id, "BTC", ANNA)]
    assert readings.asked == [account_id] * 3
    assert runs.runs == [run]
    assert (run.account_id, run.user_id, run.environment, run.started_at) == (
        account_id,
        "oid-anna",
        "prod",
        STARTED_AT,
    )
    assert run.outcome == "superata"


def test_each_step_keeps_what_it_read_or_what_its_order_did(build: Build) -> None:
    run = build(ScriptedReadings(normal_readings()), ScriptedOrders()).execute(
        RunExchangeVerificationCommand(uuid4(), ANNA)
    )

    opening, after_opening, closing, after_closing = run.steps
    assert (opening.order, closing.order) == (OPENED, CLOSED)
    assert after_opening.reading == a_reading(LONG_BTC)
    assert after_closing.reading == a_reading()


@pytest.mark.parametrize(
    ("first", "error"),
    [(a_reading(LONG_BTC), PositionAlreadyOpenError), (a_reading(margin=Decimal(5)), InsufficientMarginError)],
    ids=["position-open", "margin"],
)
def test_an_account_not_ready_does_not_start_sends_nothing_and_records_nothing(
    build: Build, runs: InMemoryVerificationRunRepositoryAdapter, first: AccountReading, error: type[Exception]
) -> None:
    orders = ScriptedOrders()

    with pytest.raises(error):
        build(ScriptedReadings([first]), orders).execute(RunExchangeVerificationCommand(uuid4(), ANNA))

    assert (orders.sent, runs.runs) == ([], [])


def test_an_account_whose_flow_trades_the_asset_does_not_start_and_is_not_read(
    build: Build, runs: InMemoryVerificationRunRepositoryAdapter
) -> None:
    account_id, orders, readings = uuid4(), ScriptedOrders(), ScriptedReadings(normal_readings())
    readings.flows[account_id, PROCEDURE_OPENING.coin] = "alfa"

    with pytest.raises(AssetOfFlowError) as raised:
        build(readings, orders).execute(RunExchangeVerificationCommand(account_id, ANNA))

    assert (str(raised.value), raised.value.status_code) == ("BTC è un asset del flusso alfa", 409)
    assert (orders.sent, runs.runs, readings.asked) == ([], [], [])


def test_a_flow_of_another_account_on_the_asset_does_not_stop_the_procedure(build: Build) -> None:
    readings = ScriptedReadings(normal_readings(), flows={(uuid4(), PROCEDURE_OPENING.coin): "alfa"})

    run = build(readings, ScriptedOrders()).execute(RunExchangeVerificationCommand(uuid4(), ANNA))

    assert run.failed_step is None


@pytest.mark.parametrize("failure", [VerificationStepError(UNREACHABLE), VerificationAccountNotFoundError()])
def test_an_account_that_cannot_be_read_before_starting_does_not_start(
    build: Build, runs: InMemoryVerificationRunRepositoryAdapter, failure: Exception
) -> None:
    orders = ScriptedOrders()

    with pytest.raises(type(failure)):
        build(ScriptedReadings([failure]), orders).execute(RunExchangeVerificationCommand(uuid4(), ANNA))

    assert (orders.sent, runs.runs) == ([], [])


def test_a_refused_opening_stops_the_run_with_the_message_of_the_exchange(
    build: Build, runs: InMemoryVerificationRunRepositoryAdapter
) -> None:
    readings, orders = ScriptedReadings(normal_readings()), ScriptedOrders(opening=REFUSED)

    run = build(readings, orders).execute(RunExchangeVerificationCommand(uuid4(), ANNA))

    (opening,) = run.steps
    assert (opening.step, opening.succeeded, opening.message) == (Step.OPENING, False, REFUSED.message)
    assert [sent[0] for sent in orders.sent] == ["open"]
    assert len(readings.asked) == 1
    assert runs.runs == [run]


def test_an_opening_that_cannot_be_sent_fails_its_step_with_the_reason(build: Build) -> None:
    orders = ScriptedOrders(opening=VerificationStepError(UNREACHABLE))

    run = build(ScriptedReadings(normal_readings()), orders).execute(RunExchangeVerificationCommand(uuid4(), ANNA))

    (opening,) = run.steps
    assert (opening.succeeded, opening.message, opening.order) == (False, UNREACHABLE, None)


def test_a_reading_after_the_opening_without_the_position_stops_before_closing(build: Build) -> None:
    readings, orders = ScriptedReadings([a_reading(), a_reading(), a_reading()]), ScriptedOrders()

    run = build(readings, orders).execute(RunExchangeVerificationCommand(uuid4(), ANNA))

    assert [(step.step, step.succeeded) for step in run.steps] == [
        (Step.OPENING, True),
        (Step.READING_AFTER_OPENING, False),
    ]
    assert run.steps[-1].message == "nessuna posizione long su BTC con leva 2 letta"
    assert run.steps[-1].reading == a_reading()
    assert [sent[0] for sent in orders.sent] == ["open"]


def test_a_reading_that_fails_stops_the_run_with_its_reason(build: Build) -> None:
    readings = ScriptedReadings([a_reading(), VerificationStepError(UNREACHABLE)])

    run = build(readings, ScriptedOrders()).execute(RunExchangeVerificationCommand(uuid4(), ANNA))

    assert (run.steps[-1].step, run.steps[-1].message, run.steps[-1].reading) == (
        Step.READING_AFTER_OPENING,
        UNREACHABLE,
        None,
    )


def test_a_refused_closing_stops_the_run_and_warns_of_the_open_position(build: Build) -> None:
    readings, orders = ScriptedReadings(normal_readings()), ScriptedOrders(closing=REFUSED)

    run = build(readings, orders).execute(RunExchangeVerificationCommand(uuid4(), ANNA))

    assert run.outcome == "fallita al passo chiusura"
    assert run.warning == "sul conto resta aperta una posizione long su BTC"
    assert len(readings.asked) == 2


def test_a_position_still_open_after_the_closing_fails_the_last_step(build: Build) -> None:
    readings = ScriptedReadings([a_reading(), a_reading(LONG_BTC), a_reading(LONG_BTC)])

    run = build(readings, ScriptedOrders()).execute(RunExchangeVerificationCommand(uuid4(), ANNA))

    assert run.outcome == "fallita al passo lettura dopo chiusura"
    assert run.steps[-1].message == "posizione su BTC ancora aperta"
