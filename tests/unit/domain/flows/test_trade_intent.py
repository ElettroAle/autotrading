from decimal import Decimal

from autotrading.domain.flows.exit_plan import ExitPlan, ExitPlanChange
from autotrading.domain.flows.trade_intent import OpenIntent, UpdateIntent
from autotrading.domain.flows.trade_side import TradeSide


def test_an_opening_intent_is_built_from_the_side_named_by_the_agent() -> None:
    assert OpenIntent.of("ETH", "short", Decimal("0.25"), 3) == OpenIntent("ETH", TradeSide.SHORT, Decimal("0.25"), 3)


def test_an_opening_intent_carries_the_exit_plan_of_the_agent() -> None:
    plan = ExitPlan(Decimal(63000), Decimal(58500), "chiusura sotto 59000")

    assert OpenIntent.of("BTC", "long", Decimal("0.1"), 2, plan).exit_plan == plan


def test_an_opening_intent_without_a_plan_has_the_empty_one() -> None:
    assert OpenIntent("BTC", TradeSide.LONG, Decimal("0.1"), 2).exit_plan == ExitPlan()


def test_an_update_intent_is_built_from_the_change_named_by_the_agent() -> None:
    intent = UpdateIntent.of("BTC", Decimal(68000), Decimal(62000), "sotto 61000", remove_target=False)

    assert intent == UpdateIntent("BTC", ExitPlanChange(Decimal(68000), Decimal(62000), "sotto 61000"))


def test_an_update_intent_may_remove_the_target() -> None:
    intent = UpdateIntent.of("BTC", None, None, None, remove_target=True)

    assert intent.plan_change == ExitPlanChange(remove_target=True)
