from decimal import Decimal

from autotrading.domain.verification.procedure import Step
from autotrading.domain.verification.reading import AccountReading
from autotrading.domain.verification.step_outcome import StepOutcome
from tests.support.verification import LONG_BTC, OPENED, REFUSED, SHORT_ETH, a_reading, a_run, passed_steps


def test_a_run_with_every_step_succeeded_has_passed() -> None:
    run = a_run(*passed_steps())

    assert (run.outcome, run.failed_step, run.warning) == ("superata", None, None)


def test_the_totals_are_the_sum_of_the_two_orders() -> None:
    run = a_run(*passed_steps())

    assert run.total_fee == Decimal("0.0109")
    assert run.realized_pnl == Decimal("-0.012")


def test_a_run_failed_at_the_opening_names_the_step_and_warns_of_nothing() -> None:
    run = a_run(StepOutcome(Step.OPENING, succeeded=False, message=REFUSED.message, order=REFUSED))

    assert (run.outcome, run.failed_step, run.warning) == ("fallita al passo apertura", Step.OPENING, None)
    assert (run.total_fee, run.realized_pnl) == (Decimal(0), Decimal(0))


def test_a_run_failed_at_the_closing_warns_that_the_position_stays_open() -> None:
    steps = passed_steps()[:2]
    run = a_run(*steps, StepOutcome(Step.CLOSING, succeeded=False, message=REFUSED.message, order=REFUSED))

    assert run.outcome == "fallita al passo chiusura"
    assert run.warning == "sul conto resta aperta una posizione long su BTC"


def test_a_run_stopped_at_the_reading_after_the_opening_warns_that_the_position_stays_open() -> None:
    reading = a_reading(SHORT_ETH)
    run = a_run(passed_steps()[0], StepOutcome(Step.READING_AFTER_OPENING, succeeded=False, reading=reading))

    assert run.outcome == "fallita al passo lettura dopo apertura"
    assert run.warning == "sul conto resta aperta una posizione long su BTC"
    assert run.total_fee == OPENED.fee


def test_a_run_failed_at_the_last_reading_warns_of_nothing_once_the_position_was_closed() -> None:
    last = StepOutcome(Step.READING_AFTER_CLOSING, succeeded=False, reading=a_reading(LONG_BTC))
    run = a_run(*passed_steps()[:3], last)

    assert (run.outcome, run.warning) == ("fallita al passo lettura dopo chiusura", None)


def test_a_reading_finds_the_positions_on_an_asset() -> None:
    reading: AccountReading = a_reading(LONG_BTC, SHORT_ETH)

    assert reading.positions_on("BTC") == (LONG_BTC,)
    assert reading.positions_on("SOL") == ()
