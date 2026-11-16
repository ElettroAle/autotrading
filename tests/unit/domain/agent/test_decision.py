"""A decision of the agent builds what it asks with the constructors of whoever checks it (R1.4.4, R1.5.1)."""

from decimal import Decimal

from autotrading.domain.agent.decision import Decision, TradeAction, TradeDirection, TradeOpening
from autotrading.domain.agent.exit_plan import ExitPlan, ExitPlanChange


def built(decision: Decision) -> tuple[object, ...]:
    return decision.intent_with(
        lambda asset, side, fraction, leverage, plan, confidence: (
            "apri",
            asset,
            side,
            fraction,
            leverage,
            plan,
            confidence,
        ),
        lambda asset: ("chiudi", asset),
        lambda asset: ("mantieni", asset),
        lambda asset, change: ("aggiorna", asset, change),
    )


def test_an_opening_carries_direction_fraction_leverage_and_confidence() -> None:
    opening = TradeOpening(TradeDirection.SHORT, Decimal("0.25"), 3)

    assert built(Decision("ETH", TradeAction.OPEN, "ribasso", 70, opening)) == (
        "apri",
        "ETH",
        "short",
        Decimal("0.25"),
        3,
        ExitPlan(),
        70,
    )


def test_an_opening_carries_its_exit_plan() -> None:
    plan = ExitPlan(Decimal(63000), Decimal(58500), "chiusura sotto 59000")
    opening = TradeOpening(TradeDirection.LONG, Decimal("0.1"), 2, plan)

    assert built(Decision("BTC", TradeAction.OPEN, "rialzo", 70, opening))[-2] == plan


def test_a_close_is_built_from_the_asset_alone() -> None:
    assert built(Decision("BTC", TradeAction.CLOSE, "uscita", 20)) == ("chiudi", "BTC")


def test_a_hold_is_built_from_the_asset_alone() -> None:
    assert built(Decision("BTC", TradeAction.HOLD, "attesa", 50)) == ("mantieni", "BTC")


def test_an_opening_without_its_fields_holds_the_asset() -> None:
    assert built(Decision("BTC", TradeAction.OPEN, "incompleta", 50)) == ("mantieni", "BTC")


def test_an_update_carries_the_change_of_the_plan() -> None:
    change = ExitPlanChange(None, Decimal(62000), None, remove_target=True)

    assert built(Decision("BTC", TradeAction.UPDATE, "protezione", 80, plan_change=change)) == (
        "aggiorna",
        "BTC",
        change,
    )


def test_an_update_without_its_change_holds_the_asset() -> None:
    assert built(Decision("BTC", TradeAction.UPDATE, "incompleta", 50)) == ("mantieni", "BTC")
