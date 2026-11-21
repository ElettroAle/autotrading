from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.loss_guard import NO_REFERENCES, LossGuard, LossReferences, at_capital
from tests.support.flows import a_configuration

AT = datetime(2026, 11, 16, tzinfo=UTC)


def snapshot(equity: str, capital: str = "1000", cashed: str = "0") -> EquitySnapshot:
    """A recorded equity made only of the capital, a realized PnL and the profits cashed out until then."""
    realized = Decimal(equity) - Decimal(capital) + Decimal(cashed)
    return EquitySnapshot(
        uuid4(), AT, Decimal(capital), realized, Decimal(0), Decimal(0), Decimal(0), cashed_profit=Decimal(cashed)
    )


def guard(
    value: str,
    *,
    daily: EquitySnapshot | None = None,
    peak: EquitySnapshot | None = None,
    capital: str = "1000",
    max_daily: str | None = "5",
    max_drawdown: str | None = "10",
    cashed: str = "0",
) -> LossGuard:
    thresholds = replace(
        a_configuration(),
        allocated_capital=Decimal(capital),
        max_daily_loss_percent=None if max_daily is None else Decimal(max_daily),
        max_drawdown_percent=None if max_drawdown is None else Decimal(max_drawdown),
    )
    return LossGuard.of(thresholds, Decimal(value), LossReferences(daily, peak), Decimal(cashed))


def test_a_daily_loss_beyond_its_threshold_suspends_the_openings() -> None:
    assert guard("940", daily=snapshot("1000")).breach() == "perdita giornaliera 6% oltre il 5%"


def test_a_loss_from_the_peak_beyond_its_threshold_suspends_the_openings() -> None:
    breach = guard("1068", daily=snapshot("1100"), peak=snapshot("1200")).breach()

    assert breach == "perdita dal picco 11% oltre il 10%"


def test_the_daily_loss_comes_first_when_both_are_beyond() -> None:
    assert guard("800", daily=snapshot("1000"), peak=snapshot("1000")).breach() == (
        "perdita giornaliera 20% oltre il 5%"
    )


def test_losses_within_the_thresholds_suspend_nothing() -> None:
    assert guard("960", daily=snapshot("1000"), peak=snapshot("1000")).breach() is None


def test_a_loss_equal_to_the_threshold_is_not_beyond_it() -> None:
    assert guard("950", daily=snapshot("1000"), peak=snapshot("1000")).breach() is None


def test_the_loss_is_rounded_to_the_cent_of_a_percent() -> None:
    assert guard("933.33", daily=snapshot("1000")).breach() == "perdita giornaliera 6,67% oltre il 5%"


def test_a_flow_without_thresholds_is_never_suspended() -> None:
    assert guard("1", daily=snapshot("1000"), peak=snapshot("1000"), max_daily=None, max_drawdown=None).breach() is None


def test_a_flow_without_recorded_equity_has_no_reference_and_is_not_suspended() -> None:
    suspended = LossGuard.of(a_configuration(), Decimal(1), NO_REFERENCES, Decimal(0))

    assert suspended.breach() is None
    assert suspended.daily_reference is None


def test_a_change_of_capital_moves_the_references_by_the_same_amount() -> None:
    reduced = guard("800", daily=snapshot("1000"), peak=snapshot("1000"), capital="800")

    assert (reduced.daily_reference, reduced.peak) == (Decimal(800), Decimal(800))
    assert reduced.breach() is None


def test_the_peak_includes_the_value_read_now() -> None:
    assert guard("1300", peak=snapshot("1200")).peak == Decimal(1300)
    assert guard("940").peak == Decimal(940)


@pytest.mark.parametrize("reference", ["0", "-10"])
def test_a_reference_without_value_measures_no_loss(reference: str) -> None:
    assert guard("-50", daily=snapshot(reference), peak=snapshot(reference)).breach() is None


def test_a_reference_is_lowered_by_the_profits_cashed_out_after_it_was_recorded() -> None:
    assert at_capital(snapshot("1150"), Decimal(1000), Decimal(150)) == Decimal(1000)


def test_the_profits_cashed_out_before_a_reference_was_recorded_do_not_move_it() -> None:
    assert at_capital(snapshot("1100", cashed="150"), Decimal(1000), Decimal(150)) == Decimal(1100)
    assert at_capital(snapshot("1100", cashed="100"), Decimal(1000), Decimal(150)) == Decimal(1050)


def test_a_reference_follows_both_a_change_of_capital_and_a_cash_out() -> None:
    assert at_capital(snapshot("1150"), Decimal(800), Decimal(150)) == Decimal(800)


def test_a_cash_out_is_not_a_loss_from_the_peak_nor_of_the_day() -> None:
    """ADR-perdita-massima-al-netto-degli-incassi: a peak of 1150 cashing out 150 is worth 1000 and lost nothing."""
    cashed_out = guard("1000", daily=snapshot("1150"), peak=snapshot("1150"), cashed="150")

    assert (cashed_out.daily_reference, cashed_out.peak) == (Decimal(1000), Decimal(1000))
    assert cashed_out.breach() is None


def test_a_real_loss_after_a_cash_out_is_still_measured() -> None:
    breach = guard("880", daily=snapshot("1000", cashed="150"), peak=snapshot("1150"), cashed="150").breach()

    assert breach == "perdita giornaliera 12% oltre il 5%"
    assert guard("890", peak=snapshot("1150"), cashed="150").breach() == "perdita dal picco 11% oltre il 10%"
