"""A decision of the agent builds what it asks with the constructors of whoever checks it (R1.4.4, R1.5.1)."""

from decimal import Decimal

from autotrading.domain.agent.decision import Decision, TradeAction, TradeDirection, TradeOpening
from autotrading.domain.agent.exit_plan import ExitPlan


def built(decision: Decision) -> tuple[object, ...]:
    return decision.intent_with(
        lambda asset, side, fraction, leverage, plan: ("apri", asset, side, fraction, leverage, plan),
        lambda asset: ("chiudi", asset),
        lambda asset: ("mantieni", asset),
    )


def test_an_opening_carries_direction_fraction_and_leverage() -> None:
    opening = TradeOpening(TradeDirection.SHORT, Decimal("0.25"), 3)

    assert built(Decision("ETH", TradeAction.OPEN, "ribasso", opening)) == (
        "apri",
        "ETH",
        "short",
        Decimal("0.25"),
        3,
        ExitPlan(),
    )


def test_an_opening_carries_its_exit_plan() -> None:
    plan = ExitPlan(Decimal(63000), Decimal(58500), "chiusura sotto 59000")
    opening = TradeOpening(TradeDirection.LONG, Decimal("0.1"), 2, plan)

    assert built(Decision("BTC", TradeAction.OPEN, "rialzo", opening))[-1] == plan


def test_a_close_is_built_from_the_asset_alone() -> None:
    assert built(Decision("BTC", TradeAction.CLOSE, "uscita")) == ("chiudi", "BTC")


def test_a_hold_is_built_from_the_asset_alone() -> None:
    assert built(Decision("BTC", TradeAction.HOLD, "attesa")) == ("mantieni", "BTC")


def test_an_opening_without_its_fields_holds_the_asset() -> None:
    assert built(Decision("BTC", TradeAction.OPEN, "incompleta")) == ("mantieni", "BTC")
