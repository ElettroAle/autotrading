from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.loss_guard import NO_REFERENCES, LossGuard, LossReferences
from tests.support.flows import a_configuration

AT = datetime(2026, 11, 16, tzinfo=UTC)


def snapshot(equity: str, capital: str = "1000") -> EquitySnapshot:
    """A recorded equity made only of the capital and a realized PnL."""
    realized = Decimal(equity) - Decimal(capital)
    return EquitySnapshot(uuid4(), AT, Decimal(capital), realized, Decimal(0), Decimal(0), Decimal(0))


def guard(
    value: str,
    *,
    daily: EquitySnapshot | None = None,
    peak: EquitySnapshot | None = None,
    capital: str = "1000",
    max_daily: str | None = "5",
    max_drawdown: str | None = "10",
) -> LossGuard:
    thresholds = replace(
        a_configuration(),
        allocated_capital=Decimal(capital),
        max_daily_loss_percent=None if max_daily is None else Decimal(max_daily),
        max_drawdown_percent=None if max_drawdown is None else Decimal(max_drawdown),
    )
    return LossGuard.of(thresholds, Decimal(value), LossReferences(daily, peak))


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
    suspended = LossGuard.of(a_configuration(), Decimal(1), NO_REFERENCES)

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
