from decimal import Decimal

import pytest

from autotrading.domain.flows.exit_plan import DiscardedLevel, ExitPlan
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
