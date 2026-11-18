from decimal import Decimal

from autotrading.domain.flows.exit_plan import ExitPlan, ExitPlanChange
from autotrading.domain.flows.trade_intent import OpenIntent, ReverseIntent, UpdateIntent
from autotrading.domain.flows.trade_side import TradeSide


def test_an_opening_intent_is_built_from_the_side_named_by_the_agent() -> None:
    intent = OpenIntent.of("ETH", "short", Decimal("0.25"), 3, 70)

    assert intent == OpenIntent("ETH", TradeSide.SHORT, Decimal("0.25"), 3, 70)


def test_an_opening_intent_carries_the_confidence_of_the_agent() -> None:
    assert OpenIntent.of("ETH", "long", Decimal("0.25"), 3, 42).confidence == 42


def test_an_opening_intent_carries_the_exit_plan_of_the_agent() -> None:
    plan = ExitPlan(Decimal(63000), Decimal(58500), "chiusura sotto 59000")

    assert OpenIntent.of("BTC", "long", Decimal("0.1"), 2, 70, plan).exit_plan == plan


def test_an_opening_intent_without_a_plan_has_the_empty_one() -> None:
    assert OpenIntent("BTC", TradeSide.LONG, Decimal("0.1"), 2, 70).exit_plan == ExitPlan()


def test_an_update_intent_is_built_from_the_change_named_by_the_agent() -> None:
    intent = UpdateIntent.of("BTC", Decimal(68000), Decimal(62000), "sotto 61000", remove_target=False)

    assert intent == UpdateIntent("BTC", ExitPlanChange(Decimal(68000), Decimal(62000), "sotto 61000"))


def test_an_update_intent_may_remove_the_target() -> None:
    intent = UpdateIntent.of("BTC", None, None, None, remove_target=True)

    assert intent.plan_change == ExitPlanChange(remove_target=True)


def test_the_margin_an_opening_asks_for_is_its_share_of_the_money_of_the_flow() -> None:
    assert OpenIntent.of("BTC", "long", Decimal("0.15"), 3, 70).margin_on(Decimal(1000)) == Decimal(150)


def test_a_reversal_intent_opens_the_side_opposite_to_the_position_open() -> None:
    plan = ExitPlan(Decimal(70000), Decimal(64000), None)
    intent = ReverseIntent("BTC", Decimal("0.2"), 3, 75, plan)

    assert intent.opening(TradeSide.SHORT) == OpenIntent("BTC", TradeSide.LONG, Decimal("0.2"), 3, 75, plan)
    assert intent.opening(TradeSide.LONG).side is TradeSide.SHORT


def test_a_reversal_intent_without_a_plan_has_the_empty_one() -> None:
    assert ReverseIntent("BTC", Decimal("0.2"), 3, 75).exit_plan == ExitPlan()


def test_the_opposite_of_a_side() -> None:
    assert (TradeSide.LONG.opposite, TradeSide.SHORT.opposite) == (TradeSide.SHORT, TradeSide.LONG)
