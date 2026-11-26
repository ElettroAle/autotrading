from decimal import Decimal

import pytest

from autotrading.domain.flows.exit_plan import DiscardedLevel, ExitPlan, ExitPlanChange, PlacedLevels
from autotrading.domain.flows.trade_side import TradeSide

MARKET = Decimal(60000)


def test_a_plan_coherent_with_a_long_keeps_every_level() -> None:
    plan = ExitPlan(Decimal(63000), Decimal(58500), "chiusura a 4 ore sotto 59000")

    assert plan.coherent_with(TradeSide.LONG, MARKET) == (plan, ())


def test_a_plan_coherent_with_a_short_keeps_every_level() -> None:
    plan = ExitPlan(Decimal(57000), Decimal(61500), None)

    assert plan.coherent_with(TradeSide.SHORT, MARKET) == (plan, ())


def test_an_empty_plan_has_nothing_to_discard() -> None:
    assert ExitPlan().coherent_with(TradeSide.LONG, MARKET) == (ExitPlan(), ())


@pytest.mark.parametrize(
    ("side", "plan", "kept", "discarded"),
    [
        (
            TradeSide.LONG,
            ExitPlan(stop=Decimal(61000)),
            ExitPlan(),
            DiscardedLevel(Decimal(61000), "stop 61000 scartato: incoerente con long al prezzo 60000"),
        ),
        (
            TradeSide.LONG,
            ExitPlan(stop=Decimal(60000)),
            ExitPlan(),
            DiscardedLevel(Decimal(60000), "stop 60000 scartato: incoerente con long al prezzo 60000"),
        ),
        (
            TradeSide.LONG,
            ExitPlan(target=Decimal(59000), stop=Decimal(58000)),
            ExitPlan(stop=Decimal(58000)),
            DiscardedLevel(Decimal(59000), "obiettivo 59000 scartato: incoerente con long al prezzo 60000"),
        ),
        (
            TradeSide.LONG,
            ExitPlan(target=Decimal(60000)),
            ExitPlan(),
            DiscardedLevel(Decimal(60000), "obiettivo 60000 scartato: incoerente con long al prezzo 60000"),
        ),
        (
            TradeSide.SHORT,
            ExitPlan(stop=Decimal(59000), invalidation="rottura di 61000"),
            ExitPlan(invalidation="rottura di 61000"),
            DiscardedLevel(Decimal(59000), "stop 59000 scartato: incoerente con short al prezzo 60000"),
        ),
        (
            TradeSide.SHORT,
            ExitPlan(target=Decimal(61000)),
            ExitPlan(),
            DiscardedLevel(Decimal(61000), "obiettivo 61000 scartato: incoerente con short al prezzo 60000"),
        ),
    ],
)
def test_a_level_incoherent_with_the_side_is_discarded_with_the_reason(
    side: TradeSide, plan: ExitPlan, kept: ExitPlan, discarded: DiscardedLevel
) -> None:
    assert plan.coherent_with(side, MARKET) == (kept, (discarded,))


def test_both_levels_incoherent_are_discarded_target_first() -> None:
    kept, discarded = ExitPlan(Decimal(59000), Decimal(61000), "x").coherent_with(TradeSide.LONG, MARKET)

    assert kept == ExitPlan(invalidation="x")
    assert [level.price for level in discarded] == [Decimal(59000), Decimal(61000)]


def test_prices_read_as_the_user_writes_them() -> None:
    _, (discarded,) = ExitPlan(stop=Decimal("60100.50")).coherent_with(TradeSide.LONG, Decimal("60000.0"))

    assert discarded.reason == "stop 60100,5 scartato: incoerente con long al prezzo 60000"


def test_the_empty_plan_is_the_default() -> None:
    assert ExitPlan() == ExitPlan(None, None, None)


def test_a_change_coherent_with_the_position_keeps_every_level() -> None:
    change = ExitPlanChange(Decimal(68000), Decimal(62000), "chiusura sotto 61000")

    assert change.coherent_with(TradeSide.LONG, Decimal(64000)) == (change, ())


def test_a_change_loses_the_levels_incoherent_with_the_position_and_keeps_the_rest() -> None:
    change = ExitPlanChange(Decimal(63000), Decimal(65000), "sotto 61000")

    kept, discarded = change.coherent_with(TradeSide.LONG, Decimal(64000))

    assert kept == ExitPlanChange(None, None, "sotto 61000")
    assert discarded == (
        DiscardedLevel(Decimal(63000), "obiettivo 63000 scartato: incoerente con long al prezzo 64000"),
        DiscardedLevel(Decimal(65000), "stop 65000 scartato: incoerente con long al prezzo 64000"),
    )


def test_a_removal_of_the_target_has_nothing_to_discard() -> None:
    change = ExitPlanChange(remove_target=True)

    assert change.coherent_with(TradeSide.SHORT, Decimal(64000)) == (change, ())


def test_the_plan_after_an_update_holds_the_levels_placed_and_the_new_invalidation() -> None:
    plan = ExitPlan(Decimal(66000), Decimal(57000), "sotto 59000")
    change = ExitPlanChange(stop=Decimal(62000), invalidation="sotto 61000", remove_target=True)

    updated = plan.updated(change, PlacedLevels(Decimal(62000), None))

    assert updated == ExitPlan(None, Decimal(62000), "sotto 61000")


def test_the_plan_after_an_update_without_invalidation_keeps_the_one_in_force() -> None:
    plan = ExitPlan(Decimal(66000), Decimal(57000), "sotto 59000")

    updated = plan.updated(ExitPlanChange(target=Decimal(68000)), PlacedLevels(Decimal(57000), Decimal(68000)))

    assert updated == ExitPlan(Decimal(68000), Decimal(57000), "sotto 59000")


def test_the_plan_in_force_holds_the_levels_placed_whatever_the_agent_asked() -> None:
    plan = ExitPlan(Decimal(63000), Decimal(55000), "sotto 59000")

    in_force = plan.in_force(PlacedLevels(Decimal(57000), Decimal(66000)))

    assert in_force == ExitPlan(Decimal(66000), Decimal(57000), "sotto 59000")


def test_the_plan_in_force_has_no_target_without_a_take_profit_placed() -> None:
    plan = ExitPlan(Decimal(63000), Decimal(57000))

    assert plan.in_force(PlacedLevels(Decimal(57000), None)) == ExitPlan(None, Decimal(57000))


def test_the_plan_in_force_of_a_position_without_a_plan_of_the_agent_is_the_levels_placed() -> None:
    assert ExitPlan().in_force(PlacedLevels(Decimal(57000), None)) == ExitPlan(None, Decimal(57000))
