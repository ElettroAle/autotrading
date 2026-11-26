from decimal import Decimal

import pytest

from autotrading.domain.flows.errors import (
    TrailingActivationNotPositiveError,
    TrailingActivationWithoutDistanceError,
    TrailingBreakevenNotPositiveError,
    TrailingDistanceOutOfRangeError,
)
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.flows.trailing_stop import TrailingStop

ENTRY = Decimal(60000)
LONG, SHORT = TradeSide.LONG, TradeSide.SHORT


def test_the_default_is_empty_and_off() -> None:
    trailing = TrailingStop()

    assert (trailing.distance_percent, trailing.activation_percent, trailing.breakeven_percent) == (None, None, None)
    assert not trailing.max_profit_in_context
    assert not trailing.active


@pytest.mark.parametrize("percent", [Decimal("0.1"), Decimal(2), Decimal(50)])
def test_accepts_a_distance_from_a_tenth_to_fifty(percent: Decimal) -> None:
    assert TrailingStop(percent).distance_percent == percent


@pytest.mark.parametrize("percent", [Decimal(0), Decimal("0.05"), Decimal(51), Decimal("NaN"), Decimal("Infinity")])
def test_refuses_a_distance_out_of_range_naming_the_setting(percent: Decimal) -> None:
    with pytest.raises(TrailingDistanceOutOfRangeError, match="la distanza dello stop che segue va da 0,1 a 50") as no:
        TrailingStop(percent)

    assert no.value.setting is FlowSetting.TRAILING_STOP_DISTANCE
    assert no.value.details == {"field": "trailing_stop.distance_percent"}


@pytest.mark.parametrize("percent", [Decimal(0), Decimal(-1), Decimal("NaN")])
def test_refuses_an_activation_not_positive_before_asking_for_the_distance(percent: Decimal) -> None:
    with pytest.raises(TrailingActivationNotPositiveError, match="l'attivazione dello stop che segue è maggiore di 0"):
        TrailingStop(activation_percent=percent)


def test_refuses_an_activation_without_the_distance() -> None:
    with pytest.raises(
        TrailingActivationWithoutDistanceError, match="l'attivazione richiede la distanza dello stop che segue"
    ) as refused:
        TrailingStop(activation_percent=Decimal(3))

    assert refused.value.setting is FlowSetting.TRAILING_STOP_ACTIVATION


@pytest.mark.parametrize("percent", [Decimal(0), Decimal(-1), Decimal("Infinity")])
def test_refuses_a_breakeven_not_positive(percent: Decimal) -> None:
    with pytest.raises(TrailingBreakevenNotPositiveError, match="il pareggio è maggiore di 0") as refused:
        TrailingStop(breakeven_percent=percent)

    assert refused.value.setting is FlowSetting.TRAILING_STOP_BREAKEVEN


def test_a_breakeven_alone_is_admitted_and_active() -> None:
    assert TrailingStop(breakeven_percent=Decimal("1.5")).active


def test_the_distance_alone_is_active() -> None:
    assert TrailingStop(Decimal(2)).active


def test_the_option_of_the_context_alone_is_not_active_and_reaches_no_agent() -> None:
    trailing = TrailingStop(max_profit_in_context=True)

    assert not trailing.active
    assert not trailing.max_profit_for_agent


def test_the_option_reaches_the_agent_only_with_the_stop_active() -> None:
    assert TrailingStop(Decimal(2), max_profit_in_context=True).max_profit_for_agent
    assert not TrailingStop(Decimal(2)).max_profit_for_agent


def test_the_changed_stop_keeps_the_parts_not_given() -> None:
    trailing = TrailingStop(Decimal(2), Decimal(3), Decimal("1.5"), max_profit_in_context=True)

    assert trailing.changed(breakeven_percent=None) == TrailingStop(Decimal(2), Decimal(3), None, True)


@pytest.mark.parametrize(
    ("side", "best", "stop"),
    [
        (LONG, Decimal(60000), Decimal(58800)),
        (LONG, Decimal(63000), Decimal(61740)),
        (SHORT, Decimal(57000), Decimal(58140)),
    ],
)
def test_the_stop_lies_at_the_distance_from_the_best_price(side: TradeSide, best: Decimal, stop: Decimal) -> None:
    assert TrailingStop(Decimal(2)).stop_of(side, ENTRY, best) == stop


@pytest.mark.parametrize(("best", "stop"), [(Decimal(61000), None), (Decimal(61800), Decimal(60564))])
def test_the_distance_follows_only_after_the_activation(best: Decimal, stop: Decimal | None) -> None:
    assert TrailingStop(Decimal(2), Decimal(3)).stop_of(LONG, ENTRY, best) == stop


def test_the_activation_of_a_short_counts_the_price_going_down() -> None:
    trailing = TrailingStop(Decimal(2), Decimal(3))

    assert trailing.stop_of(SHORT, ENTRY, Decimal(59000)) is None
    assert trailing.stop_of(SHORT, ENTRY, Decimal(58200)) == Decimal(59364)


@pytest.mark.parametrize(("best", "stop"), [(Decimal(60600), None), (Decimal(60900), ENTRY)])
def test_the_breakeven_brings_the_stop_to_the_entry_price(best: Decimal, stop: Decimal | None) -> None:
    assert TrailingStop(breakeven_percent=Decimal("1.5")).stop_of(LONG, ENTRY, best) == stop


def test_with_distance_and_breakeven_the_stop_closer_to_the_price_wins() -> None:
    trailing = TrailingStop(Decimal(2), breakeven_percent=Decimal("1.5"))

    assert trailing.stop_of(LONG, ENTRY, Decimal(60900)) == ENTRY
    assert trailing.stop_of(LONG, ENTRY, Decimal(63000)) == Decimal(61740)
    assert trailing.stop_of(SHORT, ENTRY, Decimal(59100)) == ENTRY


def test_without_the_settings_no_stop_is_computed() -> None:
    assert TrailingStop().stop_of(LONG, ENTRY, Decimal(70000)) is None


@pytest.mark.parametrize(
    ("side", "best", "in_force", "moved"),
    [
        (LONG, Decimal(60000), Decimal(57000), Decimal(58800)),
        (LONG, Decimal(63000), Decimal(61740), None),
        (LONG, Decimal(60200), Decimal(59500), None),
        (LONG, Decimal(63000), None, Decimal(61740)),
        (SHORT, Decimal(57000), Decimal(63000), Decimal(58140)),
        (SHORT, Decimal(57000), Decimal(58000), None),
    ],
)
def test_the_stop_moves_only_closer_to_the_price(
    side: TradeSide, best: Decimal, in_force: Decimal | None, moved: Decimal | None
) -> None:
    assert TrailingStop(Decimal(2)).moved_stop(side, ENTRY, best, in_force) == moved


@pytest.mark.parametrize(
    ("side", "stop", "computed", "farther"),
    [
        (LONG, Decimal(58000), Decimal(61740), True),
        (LONG, Decimal(61800), Decimal(61740), False),
        (SHORT, Decimal(60000), Decimal(58140), True),
        (SHORT, Decimal(58000), Decimal(58140), False),
    ],
)
def test_a_stop_is_farther_from_the_price_below_for_a_long_and_above_for_a_short(
    side: TradeSide, stop: Decimal, computed: Decimal, farther: bool
) -> None:
    assert TrailingStop.farther(stop, computed, side) is farther


@pytest.mark.parametrize(
    ("side", "previous", "price", "best"),
    [
        (LONG, None, Decimal(62000), Decimal(62000)),
        (LONG, Decimal(63000), Decimal(62000), Decimal(63000)),
        (LONG, Decimal(63000), Decimal(64000), Decimal(64000)),
        (SHORT, Decimal(57000), Decimal(58000), Decimal(57000)),
        (SHORT, Decimal(57000), Decimal(56000), Decimal(56000)),
    ],
)
def test_the_best_price_is_the_highest_for_a_long_and_the_lowest_for_a_short(
    side: TradeSide, previous: Decimal | None, price: Decimal, best: Decimal
) -> None:
    assert TrailingStop.best_price(side, previous, price) == best
