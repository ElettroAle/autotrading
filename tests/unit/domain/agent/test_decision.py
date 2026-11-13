"""A decision of the agent builds what it asks with the constructors of whoever checks it (R1.4.4, R1.5.1)."""

from decimal import Decimal

from autotrading.domain.agent.decision import Decision, TradeAction, TradeDirection, TradeOpening


def built(decision: Decision) -> tuple[object, ...]:
    return decision.intent_with(
        lambda asset, side, fraction, leverage: ("apri", asset, side, fraction, leverage),
        lambda asset: ("chiudi", asset),
        lambda asset: ("mantieni", asset),
    )


def test_an_opening_carries_direction_fraction_and_leverage() -> None:
    opening = TradeOpening(TradeDirection.SHORT, Decimal("0.25"), 3)

    assert built(Decision("ETH", TradeAction.OPEN, "ribasso", opening)) == ("apri", "ETH", "short", Decimal("0.25"), 3)


def test_a_close_is_built_from_the_asset_alone() -> None:
    assert built(Decision("BTC", TradeAction.CLOSE, "uscita")) == ("chiudi", "BTC")


def test_a_hold_is_built_from_the_asset_alone() -> None:
    assert built(Decision("BTC", TradeAction.HOLD, "attesa")) == ("mantieni", "BTC")


def test_an_opening_without_its_fields_holds_the_asset() -> None:
    assert built(Decision("BTC", TradeAction.OPEN, "incompleta")) == ("mantieni", "BTC")
