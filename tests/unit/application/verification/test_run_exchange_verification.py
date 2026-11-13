from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.verification.errors import VerificationAccountNotFoundError, VerificationStepError
from autotrading.application.verification.ports import (
    ProcedureAsset,
    ProcedureClosing,
    ProcedureOpening,
    ProcedureOrders,
)
from autotrading.application.verification.run_exchange_verification import (
    RunExchangeVerificationCommand,
    RunExchangeVerificationUseCase,
    VerificationReadings,
)
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.errors import (
    AmountBelowMinimumError,
    AssetOfFlowError,
    InsufficientMarginError,
    PositionAlreadyOpenError,
    VerificationInProgressError,
)
from autotrading.domain.verification.order_result import OrderResult
from autotrading.domain.verification.procedure import PROCEDURE_COIN, Opening, Step
from autotrading.domain.verification.reading import AccountReading
from tests.fakes.verification_run_repository import InMemoryVerificationRunRepositoryAdapter
from tests.support.verification import CLOSED, LONG_BTC, OPENED, REFUSED, STARTED_AT, a_reading

ANNA = UserId("oid-anna")
UNREACHABLE = "exchange non raggiungibile"
EXCHANGE_MINIMUM = Decimal(10)

Answer = AccountReading | Exception


@dataclass
class ScriptedReadings:
    """Answers the readings in order: the check before starting, then the reading steps."""

    answers: list[Answer]
    asked: list[UUID] = field(default_factory=list)
    flows: dict[tuple[UUID, str], str] = field(default_factory=dict)

    def execute(self, account_id: UUID) -> AccountReading:
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
    minimum: Decimal | Exception = EXCHANGE_MINIMUM
    sent: list[tuple[str, UUID, object, UserId]] = field(default_factory=list)
    asked_minimum: list[tuple[UUID, str]] = field(default_factory=list)
    while_opening: Callable[[], None] = lambda: None

    def minimum_value(self, account_id: UUID, coin: str) -> Decimal:
        self.asked_minimum.append((account_id, coin))
        if isinstance(self.minimum, Exception):
            raise self.minimum
        return self.minimum

    def open(self, account_id: UUID, opening: Opening, user_id: UserId) -> OrderResult:
        self.sent.append(("open", account_id, opening, user_id))
        self.while_opening()
        return _answer(self.opening)

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderResult:
        self.sent.append(("close", account_id, coin, user_id))
        return _answer(self.closing)


@dataclass(frozen=True, slots=True)
class OrderAnswer:
    """The answer of the orders context for an order of the procedure."""

    fee: Decimal | None
    realized_pnl: Decimal | None
    exchange_message: str | None
    status: str

    @classmethod
    def of(cls, result: OrderResult) -> OrderAnswer:
        if result.succeeded:
            return cls(result.fee, result.realized_pnl, None, "eseguito")
        return cls(None, None, result.message, "rifiutato")


@dataclass(frozen=True, slots=True)
class MinimumOf:
    orders: ScriptedOrders

    def execute(self, asset: ProcedureAsset) -> Decimal:
        return self.orders.minimum_value(asset.account_id, asset.coin)


@dataclass(frozen=True, slots=True)
class OpeningOf:
    orders: ScriptedOrders

    def execute(self, opening: ProcedureOpening) -> OrderAnswer:
        asked = Opening(opening.coin, opening.side, opening.leverage, opening.value)
        return OrderAnswer.of(self.orders.open(opening.account_id, asked, opening.user_id))


@dataclass(frozen=True, slots=True)
class ClosingOf:
    orders: ScriptedOrders

    def execute(self, closing: ProcedureClosing) -> OrderAnswer:
        return OrderAnswer.of(self.orders.close(closing.account_id, closing.coin, closing.user_id))


def procedure_orders(orders: ScriptedOrders) -> ProcedureOrders:
    return ProcedureOrders(MinimumOf(orders), OpeningOf(orders), ClosingOf(orders))


def an_opening(value: Decimal) -> Opening:
    return Opening(coin="BTC", side="long", leverage=2, value=value)


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
        return RunExchangeVerificationUseCase(
            VerificationReadings(readings, readings), procedure_orders(orders), runs, "prod", lambda: STARTED_AT
        )

    return use_case


def test_a_passed_run_opens_reads_closes_reads_and_is_recorded(
    build: Build, runs: InMemoryVerificationRunRepositoryAdapter
) -> None:
    account_id, readings, orders = uuid4(), ScriptedReadings(normal_readings()), ScriptedOrders()

    run = build(readings, orders).execute(RunExchangeVerificationCommand(account_id, ANNA))

    assert [(step.step, step.succeeded) for step in run.steps] == [(step, True) for step in Step]
    assert orders.sent == [("open", account_id, an_opening(EXCHANGE_MINIMUM), ANNA), ("close", account_id, "BTC", ANNA)]
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
    [(a_reading(LONG_BTC), PositionAlreadyOpenError), (a_reading(margin=Decimal("4.99")), InsufficientMarginError)],
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
    readings.flows[account_id, PROCEDURE_COIN] = "alfa"

    with pytest.raises(AssetOfFlowError) as raised:
        build(readings, orders).execute(RunExchangeVerificationCommand(account_id, ANNA))

    assert (str(raised.value), raised.value.status_code) == ("BTC è un asset del flusso alfa", 409)
    assert (orders.sent, runs.runs, readings.asked) == ([], [], [])


def test_a_flow_of_another_account_on_the_asset_does_not_stop_the_procedure(build: Build) -> None:
    readings = ScriptedReadings(normal_readings(), flows={(uuid4(), PROCEDURE_COIN): "alfa"})

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


def test_the_chosen_amount_is_the_value_of_the_opening(build: Build) -> None:
    account_id, orders = uuid4(), ScriptedOrders()

    build(ScriptedReadings(normal_readings()), orders).execute(
        RunExchangeVerificationCommand(account_id, ANNA, Decimal(20))
    )

    assert orders.sent[0] == ("open", account_id, an_opening(Decimal(20)), ANNA)
    assert orders.asked_minimum == [(account_id, "BTC")]


def test_an_amount_below_the_minimum_of_the_exchange_does_not_start(
    build: Build, runs: InMemoryVerificationRunRepositoryAdapter
) -> None:
    orders = ScriptedOrders()

    with pytest.raises(AmountBelowMinimumError) as raised:
        build(ScriptedReadings(normal_readings()), orders).execute(
            RunExchangeVerificationCommand(uuid4(), ANNA, Decimal(5))
        )

    assert (str(raised.value), raised.value.status_code) == ("importo sotto il minimo dell'exchange: 10 USDC", 409)
    assert (orders.sent, runs.runs) == ([], [])


def test_the_margin_needed_is_the_value_over_the_leverage(build: Build) -> None:
    readings = ScriptedReadings([a_reading(margin=Decimal(8))])

    with pytest.raises(InsufficientMarginError) as raised:
        build(readings, ScriptedOrders()).execute(RunExchangeVerificationCommand(uuid4(), ANNA, Decimal(20)))

    assert str(raised.value) == "margine disponibile insufficiente: servono 10 USDC"


def test_a_minimum_that_cannot_be_read_does_not_start(
    build: Build, runs: InMemoryVerificationRunRepositoryAdapter
) -> None:
    orders = ScriptedOrders(minimum=VerificationStepError(UNREACHABLE))

    with pytest.raises(VerificationStepError):
        build(ScriptedReadings(normal_readings()), orders).execute(RunExchangeVerificationCommand(uuid4(), ANNA))

    assert (orders.sent, runs.runs) == ([], [])


def test_a_procedure_in_progress_on_the_account_stops_a_second_one_before_anything_is_read(
    build: Build, runs: InMemoryVerificationRunRepositoryAdapter
) -> None:
    account_id, readings, orders = uuid4(), ScriptedReadings(normal_readings()), ScriptedOrders()
    runs.in_progress.add((account_id, "BTC"))

    with pytest.raises(VerificationInProgressError) as raised:
        build(readings, orders).execute(RunExchangeVerificationCommand(account_id, ANNA))

    assert (str(raised.value), raised.value.status_code) == ("procedura di verifica già in corso su BTC", 409)
    assert (readings.asked, orders.sent, runs.runs) == ([], [], [])


def test_the_procedure_is_in_progress_while_it_runs_and_no_longer_after(
    build: Build, runs: InMemoryVerificationRunRepositoryAdapter
) -> None:
    account_id = uuid4()
    seen: list[set[tuple[UUID, str]]] = []
    readings = ScriptedReadings(normal_readings())
    orders = ScriptedOrders(while_opening=lambda: seen.append(set(runs.in_progress)))

    build(readings, orders).execute(RunExchangeVerificationCommand(account_id, ANNA))

    assert seen == [{(account_id, "BTC")}]
    assert runs.in_progress == set()


def test_a_procedure_that_does_not_start_is_no_longer_in_progress(
    build: Build, runs: InMemoryVerificationRunRepositoryAdapter
) -> None:
    account_id = uuid4()

    with pytest.raises(PositionAlreadyOpenError):
        build(ScriptedReadings([a_reading(LONG_BTC)]), ScriptedOrders()).execute(
            RunExchangeVerificationCommand(account_id, ANNA)
        )

    assert runs.in_progress == set()
